import os
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

Effort = Literal["low", "medium", "high", "xhigh", "max"]
ProviderName = Literal["web", "academic", "reference"]


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables or `.env`."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    tavily_api_key: str = ""  # optional: without it, research uses papers + Wikipedia only

    claude_model: str = "claude-opus-5-5"
    claude_effort: Effort = "medium"
    # Server-side fallback: if a request is declined by a safety classifier,
    # the API retries it on a suitable model instead of failing the run.
    claude_fallbacks: bool = True

    # Research breadth
    max_topics: int = 5
    max_sources_per_topic: int = 6
    search_providers: list[ProviderName] = ["web", "academic", "reference"]
    results_per_query: int = 5  # web (Tavily)
    academic_results_per_query: int = 3  # OpenAlex
    reference_results_per_query: int = 2  # Wikipedia
    openalex_email: str = ""  # optional: joins OpenAlex's faster "polite pool"

    # API
    database_path: str = "researchgraph.db"
    cors_origins: list[str] = ["http://localhost:3000"]
    max_concurrent_runs: int = 3
    runs_per_hour_per_client: int = 20  # 0 disables rate limiting
    trust_proxy_headers: bool = False  # use X-Forwarded-For behind a reverse proxy
    # Scripted LLM + search with placeholder data: explore the UI without API keys.
    demo_mode: bool = False

    # Observability: LangSmith traces every graph step and model call when enabled.
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "researchgraph"

    @property
    def can_research(self) -> bool:
        """A model key plus at least one usable search provider."""
        usable = [p for p in self.search_providers if p != "web" or self.tavily_api_key]
        return bool(self.anthropic_api_key and usable)


def configure_tracing(settings: Settings) -> None:
    """LangSmith reads os.environ, which pydantic-settings does not populate from .env."""
    if settings.langsmith_tracing and settings.langsmith_api_key:
        os.environ.setdefault("LANGSMITH_TRACING", "true")
        os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key)
        os.environ.setdefault("LANGSMITH_PROJECT", settings.langsmith_project)


@lru_cache
def get_settings() -> Settings:
    return Settings()
