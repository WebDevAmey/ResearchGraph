"""Run-time dependencies injected into every node.

State is *data that changes* during a run; context is *collaborators that
don't* (the model, the search client, limits). Passing them as LangGraph
runtime context keeps nodes free of globals and lets tests swap in fakes.
"""

from dataclasses import dataclass

from app.config import Settings
from app.services.llm import ClaudeLLM, StructuredLLM
from app.services.search import (
    MultiSearch,
    OpenAlexSearchClient,
    SearchClient,
    TavilySearchClient,
    WikipediaSearchClient,
)


@dataclass(frozen=True)
class AgentContext:
    llm: StructuredLLM
    search: SearchClient
    max_topics: int = 5
    max_sources_per_topic: int = 6


def build_search(settings: Settings) -> SearchClient:
    providers: list[SearchClient] = []
    if "web" in settings.search_providers and settings.tavily_api_key:
        providers.append(TavilySearchClient(settings.tavily_api_key, settings.results_per_query))
    if "academic" in settings.search_providers:
        providers.append(
            OpenAlexSearchClient(settings.academic_results_per_query, settings.openalex_email)
        )
    if "reference" in settings.search_providers:
        providers.append(WikipediaSearchClient(settings.reference_results_per_query))
    return MultiSearch(providers)


def context_from_settings(settings: Settings) -> AgentContext:
    return AgentContext(
        llm=ClaudeLLM(settings),
        search=build_search(settings),
        max_topics=settings.max_topics,
        max_sources_per_topic=settings.max_sources_per_topic,
    )
