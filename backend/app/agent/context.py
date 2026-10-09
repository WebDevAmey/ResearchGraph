"""Run-time dependencies injected into every node.

State is *data that changes* during a run; context is *collaborators that
don't* (the model, the search client, limits). Passing them as LangGraph
runtime context keeps nodes free of globals and lets tests swap in fakes.
"""

from dataclasses import dataclass

from app.config import Settings
from app.services.llm import ClaudeLLM, StructuredLLM
from app.services.search import SearchClient, TavilySearchClient


@dataclass(frozen=True)
class AgentContext:
    llm: StructuredLLM
    search: SearchClient
    max_topics: int = 5
    max_sources_per_topic: int = 6


def context_from_settings(settings: Settings) -> AgentContext:
    return AgentContext(
        llm=ClaudeLLM(settings),
        search=TavilySearchClient(settings.tavily_api_key, settings.results_per_query),
        max_topics=settings.max_topics,
        max_sources_per_topic=settings.max_sources_per_topic,
    )
