import asyncio
import logging
from itertools import chain, zip_longest

from app.agent.schemas import Source
from app.services.search.base import SearchClient, SearchError

logger = logging.getLogger(__name__)


class MultiSearch:
    """Queries every provider concurrently and interleaves their results.

    Interleaving (web, paper, encyclopedia, web, paper, ...) keeps any one
    provider from crowding out the others before evaluation. A failing
    provider is logged and skipped; only if all of them fail is it an error.
    """

    def __init__(self, providers: list[SearchClient]) -> None:
        if not providers:
            raise ValueError("MultiSearch needs at least one provider")
        self._providers = providers

    async def search(self, query: str) -> list[Source]:
        responses = await asyncio.gather(
            *(p.search(query) for p in self._providers), return_exceptions=True
        )
        succeeded = []
        for provider, response in zip(self._providers, responses):
            if isinstance(response, BaseException):
                logger.warning("%s failed: %s", type(provider).__name__, response)
            else:
                succeeded.append(response)
        if not succeeded:
            raise SearchError(f"Every search provider failed for {query!r}")
        return [s for s in chain.from_iterable(zip_longest(*succeeded)) if s is not None]
