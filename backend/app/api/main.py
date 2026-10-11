"""HTTP API.

    POST   /api/runs              start research          → 201 RunRecord
    GET    /api/runs              recent runs (history)
    GET    /api/runs/{id}         one run, with its report when complete
    GET    /api/runs/{id}/events  Server-Sent Events: replay + live progress
    DELETE /api/runs/{id}
    GET    /api/health

Run locally:  uvicorn app.api.main:app --reload
"""

import json
import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field

from app.agent.context import AgentContext, context_from_settings
from app.agent.graph import graph as default_graph
from app.api.runs import CapacityError, RunManager
from app.api.store import RunRecord, RunStore
from app.config import Settings, get_settings
from app.demo import demo_context

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


class CreateRunRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


# --- routes ------------------------------------------------------------------


@router.get("/health")
async def health(request: Request) -> dict:
    return {
        "status": "ok",
        "configured": request.app.state.runs is not None,
        "demo": request.app.state.demo,
    }


@router.post("/runs", status_code=status.HTTP_201_CREATED)
async def create_run(body: CreateRunRequest, request: Request) -> RunRecord:
    runs: RunManager | None = request.app.state.runs
    if runs is None:
        raise HTTPException(503, "The server is missing its API keys (see .env.example).")
    question = " ".join(body.question.split())
    try:
        return await runs.start(question)
    except CapacityError as exc:
        raise HTTPException(429, str(exc)) from exc


@router.get("/runs")
async def list_runs(request: Request, limit: int = 20) -> list[RunRecord]:
    return await request.app.state.store.list_runs(min(max(limit, 1), 100))


@router.get("/runs/{run_id}")
async def get_run(run_id: str, request: Request) -> RunRecord:
    return await _require_run(request, run_id)


@router.delete("/runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_run(run_id: str, request: Request) -> None:
    run = await _require_run(request, run_id)
    if run.status == "running":
        raise HTTPException(409, "Cannot delete a run that is still in progress.")
    await request.app.state.store.delete_run(run_id)


@router.get("/runs/{run_id}/events")
async def stream_events(
    run_id: str,
    request: Request,
    last_event_id: str | None = Header(default=None),
    after: int = 0,
) -> StreamingResponse:
    await _require_run(request, run_id)
    # EventSource resends the last id it saw when it reconnects, so we resume there.
    cursor = int(last_event_id) if last_event_id and last_event_id.isdigit() else after
    runs: RunManager | None = request.app.state.runs
    store: RunStore = request.app.state.store

    async def body():
        events = runs.events(run_id, cursor) if runs else _replay(store, run_id, cursor)
        async for event in events:
            if await request.is_disconnected():
                break
            if event is None:
                yield ": keepalive\n\n"
            else:
                yield f"id: {event.seq}\ndata: {json.dumps(event.data)}\n\n"

    return StreamingResponse(
        body(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _replay(store: RunStore, run_id: str, cursor: int):
    for event in await store.events_after(run_id, cursor):
        yield event


async def _require_run(request: Request, run_id: str) -> RunRecord:
    run = await request.app.state.store.get_run(run_id)
    if run is None:
        raise HTTPException(404, "Run not found.")
    return run


# --- app factory -------------------------------------------------------------


def create_app(
    settings: Settings | None = None,
    context: AgentContext | None = None,
    graph: CompiledStateGraph | None = None,
) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        store = RunStore(settings.database_path)
        interrupted = await store.fail_interrupted_runs()
        if interrupted:
            logger.warning("Marked %d interrupted runs as failed", interrupted)

        agent_context = context
        if agent_context is None and settings.demo_mode:
            agent_context = demo_context()
            logger.warning("DEMO MODE: runs use placeholder data, not real research")
        if agent_context is None and settings.anthropic_api_key and settings.tavily_api_key:
            agent_context = context_from_settings(settings)
        if agent_context is None:
            logger.warning("API keys missing: history is readable, new runs are disabled")

        app.state.store = store
        app.state.demo = settings.demo_mode and context is None
        app.state.runs = (
            RunManager(store, agent_context, graph or default_graph, settings.max_concurrent_runs)
            if agent_context
            else None
        )
        yield
        if app.state.runs:
            await app.state.runs.shutdown()
        store.close()

    app = FastAPI(title="ResearchGraph", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
app = create_app()
