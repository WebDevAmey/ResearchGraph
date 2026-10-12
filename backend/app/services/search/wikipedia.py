"""Encyclopedic background via the Wikipedia API: free, no API key.

One request searches and returns each article's plain-text introduction.
Docs: https://www.mediawiki.org/wiki/API:Search
"""

from typing import Any

import httpx

from app.agent.schemas import Source
from app.services.search.base import MAX_FULL_TEXT, USER_AGENT, SearchError, snippet

API_URL = "https://en.wikipedia.org/w/api.php"


class WikipediaSearchClient:
    def __init__(self, max_results: int, client: httpx.AsyncClient | None = None):
        self._max_results = max_results
        self._client = client or httpx.AsyncClient(
            timeout=15.0, headers={"User-Agent": USER_AGENT}
        )

    async def search(self, query: str) -> list[Source]:
        try:
            response = await self._client.get(
                API_URL,
                params={
                    "action": "query",
                    "generator": "search",
                    "gsrsearch": query,
                    "gsrlimit": self._max_results,
                    "prop": "extracts|info",
                    "inprop": "url",
                    "explaintext": 1,
                    "exintro": 1,
                    "exlimit": self._max_results,
                    "redirects": 1,
                    "format": "json",
                    "formatversion": 2,
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SearchError(f"Wikipedia search failed for {query!r}: {exc}") from exc
        return to_sources(response.json())


def to_sources(payload: dict[str, Any]) -> list[Source]:
    pages = sorted(payload.get("query", {}).get("pages", []), key=lambda p: p.get("index", 0))
    sources = []
    for rank, page in enumerate(pages):
        extract = (page.get("extract") or "").strip()
        if not extract or not page.get("fullurl"):
            continue
        sources.append(
            Source(
                url=page["fullurl"],
                title=f"{page['title']} — Wikipedia",
                content=snippet(extract),
                full_text=extract[:MAX_FULL_TEXT],
                score=round(max(0.3, 0.8 - rank * 0.15), 2),
                provider="reference",
            )
        )
    return sources
