"""Nodes of the per-topic research subgraph (evaluation lives in evaluator.py)."""

import asyncio
import logging

from langgraph.runtime import Runtime

from app.agent.context import AgentContext
from app.agent.prompts import RESEARCHER_PROMPT
from app.agent.schemas import Finding, Source, TopicAnalysis, TopicResult
from app.agent.state import TopicState
from app.services.search import SearchClient

logger = logging.getLogger(__name__)


async def search_sources(state: TopicState, runtime: Runtime[AgentContext]) -> dict:
    candidates = await gather_sources(runtime.context.search, state["topic"].search_queries)
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
    return {"summary": analysis.summary, "findings": resolve_findings(analysis, sources)}


def finalize_topic(state: TopicState) -> dict:
    """The subgraph's single exit: package local working state into a result."""
    result = TopicResult(
        topic=state["topic"],
        summary=state.get("summary", ""),
        findings=state.get("findings", []),
        sources=state.get("sources", []),
        rejected_sources=state.get("rejected", []),
        error=state.get("error"),
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


def resolve_findings(analysis: TopicAnalysis, sources: list[Source]) -> list[Finding]:
    """Map the model's local source numbers back to URLs; drop uncited claims."""
    findings = []
    for point in analysis.key_points:
        urls = list(
            dict.fromkeys(sources[i - 1].url for i in point.source_ids if 1 <= i <= len(sources))
        )
        if urls:
            findings.append(Finding(statement=point.statement, source_urls=urls))
    return findings
