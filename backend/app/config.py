from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

Effort = Literal["low", "medium", "high", "xhigh", "max"]


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables or `.env`."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    tavily_api_key: str = ""

    claude_model: str = "claude-opus-5-5"
    claude_effort: Effort = "medium"
    # Server-side fallback: if a request is declined by a safety classifier,
    # the API retries it on a suitable model instead of failing the run.
    claude_fallbacks: bool = True

    max_topics: int = 5
    results_per_query: int = 5
    max_sources_per_topic: int = 6

    # API
    database_path: str = "researchgraph.db"
    cors_origins: list[str] = ["http://localhost:3000"]
    max_concurrent_runs: int = 3
    # Scripted LLM + search with placeholder data: explore the UI without API keys.
    demo_mode: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
