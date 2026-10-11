from langgraph.runtime import Runtime

from app.agent.citations import SourceRegistry, cited_ids, sanitize
from app.agent.context import AgentContext
from app.agent.events import SNIPPET_CHARS, emit
from app.agent.prompts import SYNTHESIZER_PROMPT
from app.agent.schemas import (
    CitedPosition,
    Conflict,
    Report,
    ReportConflict,
    ReportDraft,
    TopicResult,
)
from app.agent.state import ResearchState

_TEXT_FIELDS = (
    "executive_summary",
    "detailed_analysis",
    "conflicting_evidence",
    "limitations",
    "conclusion",
)


class InsufficientEvidenceError(Exception):
    pass


async def synthesize_report(state: ResearchState, runtime: Runtime[AgentContext]) -> dict:
    results = [r for r in state.get("topic_results", []) if r.evidence]
    if not results:
        raise InsufficientEvidenceError(
            "No usable evidence was found for this question. Try rephrasing it."
        )

    emit(runtime, "synthesis_started")
    registry = SourceRegistry()
    for result in results:
        for source in result.sources:
            registry.register(source)
    conflicts = state.get("conflicts", [])

    draft = await runtime.context.llm.generate(
        SYNTHESIZER_PROMPT,
        {
            "question": state["question"],
            "evidence": format_evidence(results, registry),
            "conflicts": format_conflicts(conflicts, registry) or "None identified.",
            "sources": "\n".join(
                f"[{s.id}] {s.title} ({s.url})" + (f" — {s.assessment.label}" if s.assessment else "")
                for s in registry.all()
            ),
        },
        ReportDraft,
    )
    return {"report": build_report(draft, registry, conflicts)}


def format_evidence(results: list[TopicResult], registry: SourceRegistry) -> str:
    blocks = []
    for result in results:
        lines = [f"## {result.topic.title}", result.summary]
        for e in result.evidence:
            markers = "".join(f"[{registry.id_for(url)}]" for url in e.source_urls)
            flag = "" if e.quote_verified else " [unverified]"
            lines.append(f"- {e.statement} {markers}{flag}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def format_conflicts(conflicts: list[Conflict], registry: SourceRegistry) -> str:
    blocks = []
    for i, c in enumerate(conflicts, start=1):
        sides = "\n".join(
            f"   - {p.stance} " + "".join(f"[{registry.id_for(u)}]" for u in p.source_urls)
            for p in c.positions
        )
        blocks.append(f"{i}. {c.question}\n{sides}\n   Why: {c.explanation}\n   Verdict: {c.verdict}")
    return "\n".join(blocks)


def build_report(draft: ReportDraft, registry: SourceRegistry, conflicts: list[Conflict]) -> Report:
    """Strip invented citations, then keep only the sources the report cites."""
    valid = {s.id for s in registry.all()}
    clean = draft.model_copy(
        update={
            **{f: sanitize(getattr(draft, f), valid) for f in _TEXT_FIELDS},
            "key_findings": [sanitize(f, valid) for f in draft.key_findings],
        }
    )
    report_conflicts = [
        ReportConflict(
            question=c.question,
            positions=[
                CitedPosition(stance=p.stance, source_ids=[registry.id_for(u) for u in p.source_urls])
                for p in c.positions
            ],
            explanation=c.explanation,
            verdict=c.verdict,
        )
        for c in conflicts
    ]
    used = cited_ids(*(getattr(clean, f) for f in _TEXT_FIELDS), *clean.key_findings)
    used |= {i for c in report_conflicts for p in c.positions for i in p.source_ids}
    return Report(
        **clean.model_dump(),
        sources=[s for s in registry.all() if s.id in used],
        conflicts=report_conflicts,
    )
