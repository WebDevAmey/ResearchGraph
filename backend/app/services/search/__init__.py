"""Search providers behind one port.

Every provider implements `SearchClient`. `MultiSearch` fans a query out to
all of them at once, so each research topic draws on the open web, the
scholarly literature, and an encyclopedia in parallel.
"""

from app.services.search.base import SearchClient, SearchError
from app.services.search.multi import MultiSearch
from app.services.search.openalex import OpenAlexSearchClient
from app.services.search.tavily import TavilySearchClient
from app.services.search.wikipedia import WikipediaSearchClient

__all__ = [
    "MultiSearch",
    "OpenAlexSearchClient",
    "SearchClient",
    "SearchError",
    "TavilySearchClient",
    "WikipediaSearchClient",
]
