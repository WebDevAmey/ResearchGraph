"""Search providers, tested against recorded response shapes (no network)."""

import httpx
import pytest

from app.agent.schemas import Source
from app.services.search import (
    MultiSearch,
    OpenAlexSearchClient,
    SearchError,
    WikipediaSearchClient,
)
from app.services.search.openalex import reconstruct_abstract
from app.services.search.tavily import to_source as tavily_to_source

OPENALEX_WORK = {
    "id": "https://openalex.org/W1",
    "doi": "https://doi.org/10.1/abc",
    "display_name": "Productivity and the four-day work week",
    "publication_year": 2025,
    "cited_by_count": 12,
    "type": "article",
    "primary_location": {
        "landing_page_url": "https://journal.example/abc",
        "source": {"display_name": "Alternative Law Journal"},
    },
    "authorships": [
        {"author": {"display_name": "Ada Lovelace"}},
        {"author": {"display_name": "Alan Turing"}},
    ],
    "abstract_inverted_index": {"Shorter": [0], "weeks": [1], "raised": [2], "output.": [3]},
}

WIKIPEDIA_PAYLOAD = {
    "query": {
        "pages": [
            {"index": 2, "title": "Workweek", "fullurl": "https://en.wikipedia.org/wiki/Workweek",
             "extract": "The workweek is the part of the week devoted to labour."},
            {"index": 1, "title": "Four-day workweek",
             "fullurl": "https://en.wikipedia.org/wiki/Four-day_workweek",
             "extract": "A four-day workweek is an arrangement where employees work four days."},
            {"index": 3, "title": "Empty", "fullurl": "https://en.wikipedia.org/wiki/Empty", "extract": ""},
        ]
    }
}


def mock_client(payload: dict, status: int = 200, seen: list | None = None) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return httpx.Response(status, json=payload)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_reconstruct_abstract_orders_words_by_position():
    assert reconstruct_abstract({"world": [1], "hello": [0, 2]}) == "hello world hello"
    assert reconstruct_abstract(None) == ""


async def test_openalex_maps_papers_with_metadata():
    seen: list[httpx.Request] = []
    client = OpenAlexSearchClient(3, email="me@example.com", client=mock_client(
        {"results": [OPENALEX_WORK, {**OPENALEX_WORK, "abstract_inverted_index": None}]}, seen=seen
    ))
    sources = await client.search("four-day week")

    assert len(sources) == 1  # the work without an abstract is skipped
    paper = sources[0]
    assert paper.url == "https://doi.org/10.1/abc"  # DOI preferred over landing page
    assert paper.provider == "academic"
    assert paper.full_text == "Shorter weeks raised output."
    assert (paper.venue, paper.published_year, paper.citations) == ("Alternative Law Journal", 2025, 12)
    assert paper.authors == ["Ada Lovelace", "Alan Turing"]
    params = seen[0].url.params
    assert params["filter"] == "has_abstract:true" and params["mailto"] == "me@example.com"


async def test_openalex_http_errors_become_search_errors():
    client = OpenAlexSearchClient(3, client=mock_client({}, status=503))
    with pytest.raises(SearchError):
        await client.search("q")


async def test_wikipedia_orders_by_rank_and_skips_empty_pages():
    client = WikipediaSearchClient(3, client=mock_client(WIKIPEDIA_PAYLOAD))
    sources = await client.search("four-day week")
    assert [s.title for s in sources] == ["Four-day workweek — Wikipedia", "Workweek — Wikipedia"]
    assert all(s.provider == "reference" for s in sources)
    assert sources[0].full_text.startswith("A four-day workweek")


def test_tavily_keeps_full_text_capped_and_reads_published_year():
    source = tavily_to_source({
        "url": "https://news.example/a", "title": "A", "content": "snippet", "score": 0.8,
        "raw_content": "x" * 20_000, "published_date": "2025-03-01",
    })
    assert source.content == "snippet"
    assert len(source.full_text) == 6000
    assert source.published_year == 2025
    assert source.body == source.full_text


class StubProvider:
    def __init__(self, result):
        self.result = result

    async def search(self, query: str) -> list[Source]:
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def src(name: str) -> Source:
    return Source(url=f"https://x/{name}", title=name, content=name)


async def test_multisearch_interleaves_providers():
    search = MultiSearch([
        StubProvider([src("w1"), src("w2"), src("w3")]),
        StubProvider([src("p1")]),
        StubProvider([src("r1"), src("r2")]),
    ])
    assert [s.title for s in await search.search("q")] == ["w1", "p1", "r1", "w2", "r2", "w3"]


async def test_multisearch_tolerates_partial_failure_but_not_total():
    partial = MultiSearch([StubProvider(RuntimeError("down")), StubProvider([src("p1")])])
    assert [s.title for s in await partial.search("q")] == ["p1"]

    total = MultiSearch([StubProvider(RuntimeError("a")), StubProvider(RuntimeError("b"))])
    with pytest.raises(SearchError):
        await total.search("q")
