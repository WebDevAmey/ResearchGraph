"""Citation bookkeeping.

Researchers cite sources by URL; the report cites them by number. The
registry assigns each unique URL a stable number, and `sanitize` removes any
marker the model invented, so every citation in the report resolves.
"""

import re

from app.agent.schemas import CitedSource, Source

_MARKER = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")


class SourceRegistry:
    def __init__(self) -> None:
        self._by_url: dict[str, CitedSource] = {}

    def register(self, source: Source) -> int:
        if source.url not in self._by_url:
            self._by_url[source.url] = CitedSource(
                id=len(self._by_url) + 1,
                url=source.url,
                title=source.title,
                assessment=source.assessment,
            )
        return self._by_url[source.url].id

    def id_for(self, url: str) -> int:
        return self._by_url[url].id

    def all(self) -> list[CitedSource]:
        return list(self._by_url.values())


def sanitize(text: str, valid_ids: set[int]) -> str:
    """Drop unknown citation ids and normalise `[1, 2]` to `[1][2]`."""

    def replace(match: re.Match[str]) -> str:
        ids = [int(n) for n in match.group(1).split(",")]
        return "".join(f"[{i}]" for i in ids if i in valid_ids)

    return _MARKER.sub(replace, text)


def cited_ids(*texts: str) -> set[int]:
    return {
        int(n)
        for text in texts
        for match in _MARKER.finditer(text)
        for n in match.group(1).split(",")
    }
