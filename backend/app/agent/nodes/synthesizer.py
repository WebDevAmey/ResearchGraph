from langgraph.runtime import Runtime

from app.agent.citations import SourceRegistry, cited_ids, sanitize
from app.agent.context import AgentContext
from app.agent.prompts import SYNTHESIZER_PROMPT
from app.agent.schemas import Report, ReportDraft, TopicResult
from app.agent.state import ResearchState


class InsufficientEvidenceError(Exception):
    pass


async def synthesize_report(state: ResearchState, runtime: Runtime[AgentContext]) -> dict:
    results = [r for r in state.get("topic_results", []) if r.findings]
    if not results:
        raise InsufficientEvidenceError(
            "No usable evidence was found for this question. Try rephrasing it."
        )

    registry = SourceRegistry()
    for result in results:
        for source in result.sources:
            registry.register(source)

    draft = await runtime.context.llm.generate(
        SYNTHESIZER_PROMPT,
        {
            "question": state["question"],
            "evidence": format_evidence(results, registry),
            "sources": "\n".join(
                f"[{s.id}] {s.title} ({s.url})" + (f" — {s.assessment.label}" if s.assessment else "")
                for s in registry.all()
            ),
        },
        ReportDraft,
    )
    return {"report": build_report(draft, registry)}


def format_evidence(results: list[TopicResult], registry: SourceRegistry) -> str:
    blocks = []
    for result in results:
        lines = [f"## {result.topic.title}", result.summary]
        for finding in result.findings:
            markers = "".join(f"[{registry.id_for(url)}]" for url in finding.source_urls)
            lines.append(f"- {finding.statement} {markers}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def build_report(draft: ReportDraft, registry: SourceRegistry) -> Report:
    """Strip invented citations, then keep only the sources the report cites."""
    valid = {s.id for s in registry.all()}
    clean = draft.model_copy(
        update={
            "executive_summary": sanitize(draft.executive_summary, valid),
            "key_findings": [sanitize(f, valid) for f in draft.key_findings],
            "detailed_analysis": sanitize(draft.detailed_analysis, valid),
            "limitations": sanitize(draft.limitations, valid),
            "conclusion": sanitize(draft.conclusion, valid),
        }
    )
    used = cited_ids(
        clean.executive_summary,
        *clean.key_findings,
        clean.detailed_analysis,
        clean.limitations,
        clean.conclusion,
    )
    return Report(
        **clean.model_dump(),
        sources=[s for s in registry.all() if s.id in used],
    )
