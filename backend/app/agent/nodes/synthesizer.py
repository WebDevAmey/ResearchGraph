from langgraph.runtime import Runtime

from app.agent.citations import SourceRegistry, first_appearance, renumber, sanitize
from app.agent.context import AgentContext
from app.agent.events import SNIPPET_CHARS, emit
from app.agent.prompts import SYNTHESIZER_PROMPT
from app.agent.schemas import (
    CitedPosition,
    Conflict,
    Report,
    ReportConflict,
    ReportDraft,
    ReportMetrics,
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
    report = build_report(draft, registry, conflicts)
    report.metrics = compute_metrics(state.get("topic_results", []), report)
    return {"report": report}


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
    """Strip invented citations, keep only cited sources, and number them 1..n in reading order."""
    valid = {s.id for s in registry.all()}
    clean = draft.model_copy(
        update={
            **{f: sanitize(getattr(draft, f), valid) for f in _TEXT_FIELDS},
            "key_findings": [sanitize(f, valid) for f in draft.key_findings],
        }
    )
    # Reading order: summary, findings, analysis, the rest, then the conflict cards.
    texts = [
        clean.executive_summary,
        *clean.key_findings,
        clean.detailed_analysis,
        clean.conflicting_evidence,
        clean.limitations,
        clean.conclusion,
    ]
    conflict_ids = [registry.id_for(u) for c in conflicts for p in c.positions for u in p.source_urls]
    order = list(dict.fromkeys([*first_appearance(*texts), *conflict_ids]))
    new_id = {old: new for new, old in enumerate(order, start=1)}

    renumbered = clean.model_copy(
        update={
            **{f: renumber(getattr(clean, f), new_id) for f in _TEXT_FIELDS},
            "key_findings": [renumber(f, new_id) for f in clean.key_findings],
        }
    )
    report_conflicts = [
        ReportConflict(
            question=c.question,
            positions=[
                CitedPosition(
                    stance=p.stance,
                    source_ids=list(dict.fromkeys(new_id[registry.id_for(u)] for u in p.source_urls)),
                )
                for p in c.positions
            ],
            explanation=c.explanation,
            verdict=c.verdict,
        )
        for c in conflicts
    ]
    by_old_id = {s.id: s for s in registry.all()}
    return Report(
        **renumbered.model_dump(),
        sources=[by_old_id[old].model_copy(update={"id": new}) for old, new in new_id.items()],
        conflicts=report_conflicts,
    )


def compute_metrics(results: list[TopicResult], report: Report) -> ReportMetrics:
    evidence = [e for r in results for e in r.evidence]
    reviewed = {s.url for r in results for s in [*r.sources, *r.rejected_sources]}
    credibility = [s.assessment.credibility for s in report.sources if s.assessment]
    providers: dict[str, int] = {}
    for source in report.sources:
        providers[source.provider] = providers.get(source.provider, 0) + 1
    return ReportMetrics(
        sources_reviewed=len(reviewed),
        sources_cited=len(report.sources),
        evidence_items=len(evidence),
        verified_quotes=sum(e.quote_verified for e in evidence),
        distinct_domains=len({s.domain for s in report.sources}),
        avg_credibility=round(sum(credibility) / len(credibility), 2) if credibility else None,
        providers=providers,
    )
