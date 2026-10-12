"""Turning the model's key points into verified evidence.

The model cites sources by local number and supplies a supporting quote.
We map numbers back to URLs, drop claims with no valid source, and check
that each quote really appears in one of its cited sources. A fabricated
quote is the clearest sign of a hallucinated claim, so we flag it.
"""

import re

from app.agent.schemas import Evidence, Source, TopicAnalysis

_QUOTE_CHARS = "\"'“”‘’«»"
_ELLIPSIS = re.compile(r"\s*(?:\.\.\.|…)\s*")


def resolve_evidence(analysis: TopicAnalysis, sources: list[Source]) -> list[Evidence]:
    evidence = []
    for point in analysis.key_points:
        cited = [sources[i - 1] for i in dict.fromkeys(point.source_ids) if 1 <= i <= len(sources)]
        if not cited:
            continue
        evidence.append(
            Evidence(
                statement=point.statement,
                quote=point.quote.strip().strip(_QUOTE_CHARS),
                quote_verified=quote_in_sources(point.quote, cited),
                source_urls=[s.url for s in cited],
            )
        )
    return evidence


def quote_in_sources(quote: str, sources: list[Source]) -> bool:
    """True if every fragment of the quote (split on ellipses) appears in one source."""
    fragments = [_normalize(f) for f in _ELLIPSIS.split(quote.strip().strip(_QUOTE_CHARS))]
    fragments = [f for f in fragments if f]
    if not fragments:
        return False
    return any(
        all(fragment in _normalize(source.body) for fragment in fragments) for source in sources
    )


def _normalize(text: str) -> str:
    text = text.lower()
    for ch in _QUOTE_CHARS:
        text = text.replace(ch, "")
    return " ".join(text.split())
