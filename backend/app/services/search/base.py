from typing import Protocol

from app.agent.schemas import Source

USER_AGENT = "ResearchGraph/0.2 (https://github.com/; research agent)"
# Full text is capped per source: enough context for analysis and quote
# checks, small enough to keep a topic's prompt to a few thousand tokens.
MAX_FULL_TEXT = 6000
SNIPPET_CHARS = 700


class SearchError(Exception):
    pass


class SearchClient(Protocol):
    async def search(self, query: str) -> list[Source]: ...


def snippet(text: str, limit: int = SNIPPET_CHARS) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"
