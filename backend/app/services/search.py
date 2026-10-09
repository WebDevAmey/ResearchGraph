"""The web search port and its Tavily adapter."""

import logging
from typing import Protocol

from langchain_core.tools import ToolException
from langchain_tavily import TavilySearch

from app.agent.schemas import Source

logger = logging.getLogger(__name__)


class SearchError(Exception):
    pass


class SearchClient(Protocol):
    async def search(self, query: str) -> list[Source]: ...


class TavilySearchClient:
    def __init__(self, api_key: str, max_results: int) -> None:
        kwargs = {"tavily_api_key": api_key} if api_key else {}
        self._tool = TavilySearch(max_results=max_results, search_depth="advanced", **kwargs)

    async def search(self, query: str) -> list[Source]:
        try:
            response = await self._tool.ainvoke({"query": query})
        except ToolException:
            # Tavily raises when a query has no results; that's not a failure.
            return []
        if "error" in response:
            raise SearchError(f"Tavily search failed for {query!r}: {response['error']}")
        return [
            Source(
                url=r["url"],
                title=r.get("title") or r["url"],
                content=r.get("content") or "",
                score=r.get("score") or 0.0,
            )
            for r in response.get("results", [])
            if r.get("url")
        ]
