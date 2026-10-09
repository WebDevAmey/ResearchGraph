"""Checks the request we would send to Claude, without calling the API."""

from langchain_core.messages import HumanMessage

from app.agent.schemas import ResearchPlan
from app.config import Settings
from app.services.llm import ClaudeLLM


def payload_for(settings: Settings) -> dict:
    llm = ClaudeLLM(settings)
    bound = llm.structured(ResearchPlan).first  # the model with structured-output kwargs bound
    return bound.bound._get_request_payload([HumanMessage("hi")], **bound.kwargs)


def test_payload_uses_native_structured_output_and_effort():
    payload = payload_for(Settings(anthropic_api_key="test", claude_effort="high"))
    assert payload["model"] == "claude-opus-5-5"
    assert payload["output_config"]["effort"] == "high"
    assert payload["output_config"]["format"]["type"] == "json_schema"
    assert "tool_choice" not in payload
    assert "temperature" not in payload


def test_fallbacks_toggle():
    on = payload_for(Settings(anthropic_api_key="test"))
    assert on["fallbacks"] == "default"
    assert "server-side-fallback-2026-07-01" in on["betas"]

    off = payload_for(Settings(anthropic_api_key="test", claude_fallbacks=False))
    assert "fallbacks" not in off
