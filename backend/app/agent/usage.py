"""Token and cost accounting for a run.

`UsageTracker` is a LangChain callback. Attached once to the graph's config,
LangGraph propagates it to every model call made inside any node (Python
3.11+ carries the run's config through contextvars), so nodes need no
accounting code of their own.
"""

from typing import Any

from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.outputs import LLMResult
from pydantic import BaseModel

# USD per million tokens (input, output). Thinking tokens bill as output.
PRICES: dict[str, tuple[float, float]] = {
    "claude-fable-5-1": (10.0, 50.0),
    "claude-opus-5-5": (4.0, 20.0),
    "claude-opus-5": (5.0, 25.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-5-5": (0.10, 0.50),
}


class RunUsage(BaseModel):
    calls: int
    input_tokens: int
    output_tokens: int
    cost_usd: float | None  # None if any model's price is unknown


class UsageTracker(UsageMetadataCallbackHandler):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        with self._lock:
            self.calls += 1
        super().on_llm_end(response, **kwargs)

    def summary(self) -> RunUsage:
        input_tokens = output_tokens = 0
        cost: float | None = 0.0
        for model, usage in self.usage_metadata.items():
            input_tokens += usage.get("input_tokens", 0)
            output_tokens += usage.get("output_tokens", 0)
            price = _price(model)
            if price is None or cost is None:
                cost = None
            else:
                cost += (
                    usage.get("input_tokens", 0) * price[0]
                    + usage.get("output_tokens", 0) * price[1]
                ) / 1_000_000
        return RunUsage(
            calls=self.calls,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=round(cost, 4) if cost is not None else None,
        )


def _price(model: str) -> tuple[float, float] | None:
    # Responses may name a dated snapshot of the requested model; match by prefix.
    for name in sorted(PRICES, key=len, reverse=True):
        if model.startswith(name):
            return PRICES[name]
    return None
