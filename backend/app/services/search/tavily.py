"""General web search via Tavily, with full page text for analysis."""

from typing import Any

from langchain_core.tools import ToolException
from langchain_tavily import TavilySearch

from app.agent.schemas import Source
from app.services.search.base import MAX_FULL_TEXT, SearchError, snippet


class TavilySearchClient:
    def __init__(self, api_key: str, max_results: int) -> None:
        kwargs = {"tavily_api_key": api_key} if api_key else {}
        self._tool = TavilySearch(
            max_results=max_results,
            search_depth="advanced",
            include_raw_content="text",  # whole page, so analysis isn't limited to snippets
            **kwargs,
        )

    async def search(self, query: str) -> list[Source]:
        try:
            response = await self._tool.ainvoke({"query": query})
        except ToolException:
            # Tavily raises when a query has no results; that's not a failure.
            return []
        if "error" in response:
            raise SearchError(f"Tavily search failed for {query!r}: {response['error']}")
        return [to_source(r) for r in response.get("results", []) if r.get("url")]


def to_source(result: dict[str, Any]) -> Source:
    content = result.get("content") or ""
    raw = (result.get("raw_content") or "").strip()
    published = result.get("published_date") or ""
    return Source(
        url=result["url"],
        title=result.get("title") or result["url"],
        content=snippet(content),
        full_text=raw[:MAX_FULL_TEXT] if raw else "",
        score=result.get("score") or 0.0,
        provider="web",
        published_year=int(published[:4]) if published[:4].isdigit() else None,
    )
