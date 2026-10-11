"""Cross-topic contradiction detection.

Runs once, after every research branch has finished, because conflicts
usually span topics: one study from "clinical trials" against another from
"observational data". Evidence is numbered globally so the model can point
at specific items; code maps those numbers back to source URLs.
"""

import logging

from langgraph.runtime import Runtime

from app.agent.context import AgentContext
from app.agent.prompts import CONFLICT_PROMPT
from app.agent.schemas import Conflict, ConflictAnalysis, Evidence, Position
from app.agent.state import ResearchState

logger = logging.getLogger(__name__)


async def detect_conflicts(state: ResearchState, runtime: Runtime[AgentContext]) -> dict:
    evidence = [e for r in state.get("topic_results", []) for e in r.evidence]
    distinct_sources = {url for e in evidence for url in e.source_urls}
    if len(evidence) < 2 or len(distinct_sources) < 2:
        return {"conflicts": []}  # nothing to compare

    try:
        analysis = await runtime.context.llm.generate(
            CONFLICT_PROMPT,
            {"question": state["question"], "evidence": format_numbered_evidence(evidence)},
            ConflictAnalysis,
        )
        conflicts = resolve_conflicts(analysis, evidence)
    except Exception:
        # Conflict detection enriches the report; it is not worth failing the run.
        logger.exception("Conflict detection failed")
        conflicts = []

    return {"conflicts": conflicts}


def format_numbered_evidence(evidence: list[Evidence]) -> str:
    lines = []
    for i, e in enumerate(evidence, start=1):
        flag = "" if e.quote_verified else " [unverified]"
        lines.append(f"[{i}]{flag} {e.statement}\n    Quote: \"{e.quote}\"")
    return "\n".join(lines)


def resolve_conflicts(analysis: ConflictAnalysis, evidence: list[Evidence]) -> list[Conflict]:
    """Map evidence numbers to source URLs; keep conflicts with two or more grounded sides."""
    conflicts = []
    for finding in analysis.conflicts:
        positions = []
        for side in finding.sides:
            urls = list(
                dict.fromkeys(
                    url
                    for i in side.evidence_ids
                    if 1 <= i <= len(evidence)
                    for url in evidence[i - 1].source_urls
                )
            )
            if urls:
                positions.append(Position(stance=side.stance, source_urls=urls))
        if len(positions) >= 2:
            conflicts.append(
                Conflict(
                    question=finding.question,
                    positions=positions,
                    explanation=finding.explanation,
                    verdict=finding.verdict,
                )
            )
    return conflicts
