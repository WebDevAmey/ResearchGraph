"""In-memory stand-ins for the LLM and search ports."""

import asyncio
from collections.abc import Callable
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from app.agent.schemas import Source, SourceAssessment, SourceEvaluation


class FakeLLM:
    """Returns a canned response per output schema; records every call."""

    def __init__(self, responses: dict[type[BaseModel], BaseModel | Callable[[dict], BaseModel]]):
        self.responses = responses
        self.calls: list[tuple[type[BaseModel], dict[str, Any], str | None]] = []

    async def generate(
        self, prompt: ChatPromptTemplate, variables: dict[str, Any], schema, *, effort=None
    ):
        prompt.format_messages(**variables)  # fail loudly on missing template variables
        self.calls.append((schema, variables, effort))
        response = self.responses[schema]
        if isinstance(response, Exception):
            raise response
        return response(variables) if callable(response) else response

    def calls_for(self, schema: type[BaseModel]) -> list[dict[str, Any]]:
        return [v for s, v, _ in self.calls if s is schema]

    def efforts_for(self, schema: type[BaseModel]) -> list[str | None]:
        return [e for s, _, e in self.calls if s is schema]


class FakeSearch:
    """Serves results per query; an Exception value makes that query fail."""

    def __init__(self, results: dict[str, list[Source] | Exception], delay: float = 0.01):
        self.results = results
        self.delay = delay
        self.in_flight = 0
        self.max_in_flight = 0

    async def search(self, query: str) -> list[Source]:
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            await asyncio.sleep(self.delay)
            result = self.results.get(query, [])
            if isinstance(result, Exception):
                raise result
            return result
        finally:
            self.in_flight -= 1


def source(n: int, score: float = 0.5) -> Source:
    return Source(
        url=f"https://example.com/{n}", title=f"Source {n}", content=f"Content {n}", score=score
    )


def assessment(source_id: int, relevance: int = 4, credibility: int = 4) -> SourceAssessment:
    return SourceAssessment(
        source_id=source_id,
        relevance=relevance,
        credibility=credibility,
        source_type="news",
        published_year=2025,
        reason="test",
    )


# Approves every source in a batch of up to 10.
APPROVE_ALL = SourceEvaluation(assessments=[assessment(i) for i in range(1, 11)])
