"""Nodes of the per-topic research subgraph (evaluation lives in evaluator.py)."""

import asyncio
import logging

from langgraph.runtime import Runtime

from app.agent.context import AgentContext
from app.agent.events import emit
from app.agent.evidence import resolve_evidence
from app.agent.prompts import RESEARCHER_PROMPT
from app.agent.schemas import Source, TopicAnalysis, TopicResult
from app.agent.state import TopicState
from app.services.search import SearchClient

logger = logging.getLogger(__name__)


async def search_sources(state: TopicState, runtime: Runtime[AgentContext]) -> dict:
    emit(runtime, "topic_started", topic_id=state["topic_id"])
    candidates = await gather_sources(runtime.context.search, state["topic"].search_queries)
    emit(runtime, "sources_found", topic_id=state["topic_id"], count=len(candidates))
    if not candidates:
        return {"candidates": [], "error": "No sources found."}
    return {"candidates": candidates}


async def analyze_topic(state: TopicState, runtime: Runtime[AgentContext]) -> dict:
    sources = state["sources"]
    try:
        analysis = await runtime.context.llm.generate(
            RESEARCHER_PROMPT,
            {
                "question": state["question"],
                "topic": state["topic"].question,
                "sources": format_sources(sources),
            },
            TopicAnalysis,
        )
    except Exception as exc:
        # One failed branch must not sink the whole run; the synthesizer
        # works with whatever the other branches found.
        logger.exception("Analysis failed for topic %r", state["topic"].title)
        return {"error": str(exc)}
    return {"summary": analysis.summary, "evidence": resolve_evidence(analysis, sources)}


def finalize_topic(state: TopicState, runtime: Runtime[AgentContext]) -> dict:
    """The subgraph's single exit: package local working state into a result."""
    result = TopicResult(
        topic_id=state["topic_id"],
        topic=state["topic"],
        summary=state.get("summary", ""),
        evidence=state.get("evidence", []),
        sources=state.get("sources", []),
        rejected_sources=state.get("rejected", []),
        error=state.get("error"),
    )
    emit(
        runtime,
        "topic_completed",
        topic_id=result.topic_id,
        summary=result.summary,
        evidence_count=len(result.evidence),
        error=result.error,
    )
    return {"topic_results": [result]}


async def gather_sources(search: SearchClient, queries: list[str]) -> list[Source]:
    """Run all queries concurrently and merge results, deduplicated by URL."""
    responses = await asyncio.gather(*(search.search(q) for q in queries), return_exceptions=True)
    by_url: dict[str, Source] = {}
    for query, response in zip(queries, responses):
        if isinstance(response, BaseException):
            logger.warning("Search failed for %r: %s", query, response)
            continue
        for source in response:
            by_url.setdefault(source.url, source)
    return list(by_url.values())


def format_sources(sources: list[Source]) -> str:
    return "\n\n".join(
        f"[{i}] {s.title}"
        + (f" ({s.assessment.label})" if s.assessment else "")
        + f"\nURL: {s.url}\n{s.content}"
        for i, s in enumerate(sources, start=1)
    )
