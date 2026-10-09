import asyncio
import logging

from langgraph.runtime import Runtime

from app.agent.context import AgentContext
from app.agent.prompts import RESEARCHER_PROMPT
from app.agent.schemas import Finding, Source, TopicAnalysis, TopicResult
from app.agent.state import TopicTask
from app.services.search import SearchClient

logger = logging.getLogger(__name__)


async def research_topic(task: TopicTask, runtime: Runtime[AgentContext]) -> dict:
    ctx = runtime.context
    topic = task["topic"]
    try:
        sources = await gather_sources(ctx.search, topic.search_queries)
        if not sources:
            return _result(TopicResult(topic=topic, error="No sources found."))

        analysis = await ctx.llm.generate(
            RESEARCHER_PROMPT,
            {
                "question": task["question"],
                "topic": topic.question,
                "sources": format_sources(sources),
            },
            TopicAnalysis,
        )
        findings = resolve_findings(analysis, sources)
        return _result(
            TopicResult(topic=topic, summary=analysis.summary, findings=findings, sources=sources)
        )
    except Exception as exc:
        # One failed branch must not sink the whole run; the synthesizer
        # works with whatever the other branches found.
        logger.exception("Research failed for topic %r", topic.title)
        return _result(TopicResult(topic=topic, error=str(exc)))


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
        f"[{i}] {s.title}\nURL: {s.url}\n{s.content}" for i, s in enumerate(sources, start=1)
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


def _result(result: TopicResult) -> dict:
    return {"topic_results": [result]}
