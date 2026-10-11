"""Background research runs and their live event streams.

`start()` persists a run and launches the graph as an asyncio task, so the
HTTP request returns immediately. As the graph emits progress events, each
is appended to the store and listeners are woken via a per-run Condition.

`events()` serves both live and finished runs: it replays stored events
after a cursor, then waits for new ones until the run reaches a terminal
event. In-process signalling is enough for a single server process.
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

from langgraph.graph.state import CompiledStateGraph

from app.agent.context import AgentContext
from app.agent.nodes.synthesizer import InsufficientEvidenceError
from app.api.store import RunRecord, RunStore, StoredEvent

logger = logging.getLogger(__name__)

TERMINAL_EVENTS = {"report_ready", "run_failed"}
KEEPALIVE_SECONDS = 15.0


class CapacityError(Exception):
    pass


class RunManager:
    def __init__(
        self,
        store: RunStore,
        context: AgentContext,
        graph: CompiledStateGraph,
        max_concurrent: int = 3,
    ) -> None:
        self._store = store
        self._context = context
        self._graph = graph
        self._max_concurrent = max_concurrent
        self._signals: dict[str, asyncio.Condition] = {}  # active runs only
        self._latest: dict[str, int] = {}  # newest event seq per active run
        self._tasks: set[asyncio.Task] = set()

    async def start(self, question: str) -> RunRecord:
        if len(self._signals) >= self._max_concurrent:
            raise CapacityError("Too many research runs in progress. Try again shortly.")
        run_id = uuid4().hex
        record = await self._store.create_run(run_id, question)
        self._signals[run_id] = asyncio.Condition()
        self._latest[run_id] = 0
        task = asyncio.create_task(self._execute(run_id, question))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return record

    async def events(self, run_id: str, after_seq: int = 0) -> AsyncIterator[StoredEvent | None]:
        """Yield events after `after_seq`; `None` means "still working" (send a keepalive)."""
        while True:
            for event in await self._store.events_after(run_id, after_seq):
                yield event
                after_seq = event.seq
                if event.data["type"] in TERMINAL_EVENTS:
                    return

            signal = self._signals.get(run_id)
            if signal is None:
                return  # run is not active and its stored events are exhausted

            async with signal:
                try:
                    await asyncio.wait_for(
                        signal.wait_for(
                            lambda: self._latest.get(run_id, after_seq + 1) > after_seq
                        ),
                        timeout=KEEPALIVE_SECONDS,
                    )
                except TimeoutError:
                    yield None

    async def shutdown(self) -> None:
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

    # --- execution ----------------------------------------------------------

    async def _execute(self, run_id: str, question: str) -> None:
        try:
            await self._publish(run_id, {"type": "run_started", "question": question})
            report = None
            # Two stream modes at once, including subgraphs: "custom" carries the
            # nodes' progress events, "updates" lets us catch the final report.
            async for namespace, mode, chunk in self._graph.astream(
                {"question": question},
                context=self._context,
                stream_mode=["custom", "updates"],
                subgraphs=True,
            ):
                if mode == "custom":
                    await self._publish(run_id, chunk)
                elif not namespace and "synthesize_report" in chunk:
                    report = chunk["synthesize_report"]["report"]

            if report is None:
                raise RuntimeError("Graph finished without producing a report.")
            payload = report.model_dump(mode="json")
            await self._store.complete_run(run_id, payload)
            await self._publish(run_id, {"type": "report_ready", "report": payload})
        except InsufficientEvidenceError as exc:
            await self._fail(run_id, str(exc))
        except asyncio.CancelledError:
            await self._fail(run_id, "The run was cancelled.")
            raise
        except Exception:
            logger.exception("Run %s failed", run_id)
            await self._fail(run_id, "Research failed unexpectedly. Please try again.")
        finally:
            signal = self._signals.pop(run_id, None)
            self._latest.pop(run_id, None)
            if signal:
                async with signal:
                    signal.notify_all()

    async def _publish(self, run_id: str, data: dict[str, Any]) -> None:
        seq = await self._store.append_event(run_id, data)
        signal = self._signals.get(run_id)
        if signal:
            async with signal:
                self._latest[run_id] = seq
                signal.notify_all()

    async def _fail(self, run_id: str, message: str) -> None:
        await self._store.fail_run(run_id, message)
        await self._publish(run_id, {"type": "run_failed", "error": message})
