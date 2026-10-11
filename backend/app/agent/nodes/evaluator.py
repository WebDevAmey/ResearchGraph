"""Source evaluation: the model judges each source, code decides what to keep.

Keeping the decision rule in code (thresholds, weights, cap) makes it
deterministic, testable, and tunable without touching prompts.
"""

import logging

from langgraph.runtime import Runtime

from app.agent.context import AgentContext
from app.agent.events import emit, source_payload
from app.agent.prompts import EVALUATOR_PROMPT
from app.agent.schemas import Assessment, Source, SourceAssessment, SourceEvaluation
from app.agent.state import TopicState

logger = logging.getLogger(__name__)

MIN_RELEVANCE = 3
MIN_CREDIBILITY = 2
RELEVANCE_WEIGHT = 0.6
CREDIBILITY_WEIGHT = 0.4


async def evaluate_sources(state: TopicState, runtime: Runtime[AgentContext]) -> dict:
    update = await _evaluate(state, runtime.context)
    emit(
        runtime,
        "sources_evaluated",
        topic_id=state["topic_id"],
        kept=[source_payload(s) for s in update["sources"]],
        rejected=len(update["rejected"]),
    )
    return update


async def _evaluate(state: TopicState, ctx: AgentContext) -> dict:
    candidates = [s for s in state["candidates"] if s.content.strip()]
    try:
        evaluation = await ctx.llm.generate(
            EVALUATOR_PROMPT,
            {
                "question": state["question"],
                "topic": state["topic"].question,
                "sources": format_candidates(candidates),
            },
            SourceEvaluation,
            effort="low",
        )
    except Exception:
        # Degrade, don't fail: fall back to the search engine's own ranking.
        logger.exception("Source evaluation failed for %r", state["topic"].title)
        kept, rejected = split(candidates, by_search_score(candidates)[: ctx.max_sources_per_topic])
        return {"sources": kept, "rejected": rejected}

    kept, rejected = select_sources(candidates, evaluation.assessments, ctx.max_sources_per_topic)
    update = {"sources": kept, "rejected": rejected}
    if not kept:
        update["error"] = "No sources passed quality review."
    return update


def select_sources(
    candidates: list[Source], assessments: list[SourceAssessment], limit: int
) -> tuple[list[Source], list[Source]]:
    """Attach assessments, keep sources above the thresholds, best first, up to `limit`."""
    by_id = {a.source_id: a for a in assessments if 1 <= a.source_id <= len(candidates)}
    assessed = [
        c.model_copy(update={"assessment": to_assessment(by_id[i])}) if i in by_id else c
        for i, c in enumerate(candidates, start=1)
    ]
    passing = [s for s in assessed if s.assessment and passes(s.assessment)]
    passing.sort(key=lambda s: s.assessment.quality, reverse=True)
    return split(assessed, passing[:limit])


def to_assessment(raw: SourceAssessment) -> Assessment:
    relevance, credibility = clamp(raw.relevance), clamp(raw.credibility)
    quality = (RELEVANCE_WEIGHT * (relevance - 1) + CREDIBILITY_WEIGHT * (credibility - 1)) / 4
    return Assessment(
        relevance=relevance,
        credibility=credibility,
        source_type=raw.source_type,
        published_year=raw.published_year,
        reason=raw.reason,
        quality=round(quality, 3),
    )


def passes(assessment: Assessment) -> bool:
    return assessment.relevance >= MIN_RELEVANCE and assessment.credibility >= MIN_CREDIBILITY


def clamp(score: int) -> int:
    return max(1, min(5, score))


def by_search_score(sources: list[Source]) -> list[Source]:
    return sorted(sources, key=lambda s: s.score, reverse=True)


def split(all_sources: list[Source], kept: list[Source]) -> tuple[list[Source], list[Source]]:
    kept_urls = {s.url for s in kept}
    rejected = [s for s in all_sources if s.url not in kept_urls]
    return kept, rejected


def format_candidates(sources: list[Source]) -> str:
    return "\n\n".join(
        f"[{i}] {s.title}\nURL: {s.url}\n{s.content}" for i, s in enumerate(sources, start=1)
    )
