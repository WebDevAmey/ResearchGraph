"""Scholarly search via OpenAlex: 250M+ papers, free, no API key.

Returns peer-reviewed and preprint literature with real metadata (venue,
year, authors, citation count) that the evaluator uses to judge credibility.
Docs: https://docs.openalex.org
"""

from typing import Any

import httpx

from app.agent.schemas import Source
from app.services.search.base import MAX_FULL_TEXT, USER_AGENT, SearchError, snippet

API_URL = "https://api.openalex.org/works"
_FIELDS = (
    "id,doi,display_name,publication_year,cited_by_count,type,"
    "primary_location,authorships,abstract_inverted_index,relevance_score"
)


class OpenAlexSearchClient:
    def __init__(self, max_results: int, email: str = "", client: httpx.AsyncClient | None = None):
        self._max_results = max_results
        # Including a contact email joins OpenAlex's faster "polite pool".
        self._params = {"mailto": email} if email else {}
        self._client = client or httpx.AsyncClient(
            timeout=15.0, headers={"User-Agent": USER_AGENT}
        )

    async def search(self, query: str) -> list[Source]:
        try:
            response = await self._client.get(
                API_URL,
                params={
                    "search": query,
                    "filter": "has_abstract:true",
                    "per_page": self._max_results,
                    "select": _FIELDS,
                    **self._params,
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SearchError(f"OpenAlex search failed for {query!r}: {exc}") from exc
        results = response.json().get("results", [])
        return [s for i, work in enumerate(results) if (s := to_source(work, rank=i))]


def to_source(work: dict[str, Any], rank: int = 0) -> Source | None:
    abstract = reconstruct_abstract(work.get("abstract_inverted_index"))
    title = work.get("display_name")
    if not abstract or not title:
        return None
    location = work.get("primary_location") or {}
    url = work.get("doi") or location.get("landing_page_url") or work.get("id")
    authors = [
        a["author"]["display_name"]
        for a in (work.get("authorships") or [])[:3]
        if a.get("author", {}).get("display_name")
    ]
    return Source(
        url=url,
        title=title,
        content=snippet(abstract),
        full_text=abstract[:MAX_FULL_TEXT],
        score=round(max(0.3, 0.95 - rank * 0.1), 2),  # rank order; raw scores aren't normalised
        provider="academic",
        published_year=work.get("publication_year"),
        authors=authors,
        venue=(location.get("source") or {}).get("display_name"),
        citations=work.get("cited_by_count"),
    )


def reconstruct_abstract(inverted: dict[str, list[int]] | None) -> str:
    """OpenAlex stores abstracts as {word: [positions]}; rebuild the text."""
    if not inverted:
        return ""
    positions = {pos: word for word, places in inverted.items() for pos in places}
    return " ".join(positions[i] for i in sorted(positions))
