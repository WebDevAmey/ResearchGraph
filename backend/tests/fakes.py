"""In-memory stand-ins for the LLM and search ports."""

import asyncio
from collections.abc import Callable
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from app.agent.schemas import Source


class FakeLLM:
    """Returns a canned response per output schema; records every call."""

    def __init__(self, responses: dict[type[BaseModel], BaseModel | Callable[[dict], BaseModel]]):
        self.responses = responses
        self.calls: list[tuple[type[BaseModel], dict[str, Any]]] = []

    async def generate(self, prompt: ChatPromptTemplate, variables: dict[str, Any], schema):
        prompt.format_messages(**variables)  # fail loudly on missing template variables
        self.calls.append((schema, variables))
        response = self.responses[schema]
        return response(variables) if callable(response) else response

    def calls_for(self, schema: type[BaseModel]) -> list[dict[str, Any]]:
        return [v for s, v in self.calls if s is schema]


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


def source(n: int) -> Source:
    return Source(url=f"https://example.com/{n}", title=f"Source {n}", content=f"Content {n}")
