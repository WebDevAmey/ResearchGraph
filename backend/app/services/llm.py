"""The LLM port and its Claude adapter.

Nodes depend on the small `StructuredLLM` protocol, not on LangChain or
Anthropic directly. That keeps node logic testable with a fake and makes
the model provider a one-file change.
"""

from typing import Any, Protocol, TypeVar

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from pydantic import BaseModel

from app.config import Settings

T = TypeVar("T", bound=BaseModel)


class StructuredLLM(Protocol):
    async def generate(
        self, prompt: ChatPromptTemplate, variables: dict[str, Any], schema: type[T]
    ) -> T: ...


def build_chat_model(settings: Settings) -> ChatAnthropic:
    extra: dict[str, Any] = {}
    betas: list[str] = []
    if settings.claude_fallbacks:
        betas.append("server-side-fallback-2026-07-01")
        extra["fallbacks"] = "default"

    # No temperature and no `thinking` override: current Claude models run
    # adaptive thinking by default and reject sampling parameters. `effort`
    # is the knob for depth vs. cost.
    return ChatAnthropic(
        model=settings.claude_model,
        api_key=settings.anthropic_api_key or None,
        max_tokens=16_000,
        output_config={"effort": settings.claude_effort},
        betas=betas or None,
        model_kwargs=extra,
        max_retries=3,
    )


class ClaudeLLM:
    def __init__(self, settings: Settings) -> None:
        self._model = build_chat_model(settings)
        self._structured: dict[type[BaseModel], Runnable] = {}

    def structured(self, schema: type[T]) -> Runnable:
        # `json_schema` uses Claude's native structured outputs. The default
        # `function_calling` method forces a tool call, which current models reject.
        if schema not in self._structured:
            self._structured[schema] = self._model.with_structured_output(
                schema, method="json_schema"
            )
        return self._structured[schema]

    async def generate(
        self, prompt: ChatPromptTemplate, variables: dict[str, Any], schema: type[T]
    ) -> T:
        return await (prompt | self.structured(schema)).ainvoke(variables)
