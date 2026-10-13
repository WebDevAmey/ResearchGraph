import json
from contextlib import asynccontextmanager

import httpx
import pytest

from app.agent.context import AgentContext
from app.api.main import create_app
from app.api.store import RunStore
from app.config import Settings
from app.agent.schemas import (
    ConflictAnalysis,
    KeyPoint,
    ReportDraft,
    ResearchPlan,
    SourceEvaluation,
    Topic,
    TopicAnalysis,
)
from tests.fakes import APPROVE_ALL, FakeLLM, FakeSearch, source

PLAN = ResearchPlan(
    time_sensitive=False, understanding="u", topics=[Topic(title="A", question="qa", search_queries=["a"])]
)
RESPONSES = {
    ResearchPlan: PLAN,
    SourceEvaluation: APPROVE_ALL,
    TopicAnalysis: TopicAnalysis(
        summary="s", key_points=[KeyPoint(statement="c", quote="Content", source_ids=[1])]
    ),
    ConflictAnalysis: ConflictAnalysis(conflicts=[]),
    ReportDraft: ReportDraft(
        title="The answer", executive_summary="e [1]", key_findings=["f [1]"],
        detailed_analysis="d", conflicting_evidence="none", limitations="l", conclusion="c",
    ),
}


def settings(**overrides) -> Settings:
    return Settings(
        _env_file=None, database_path=":memory:", anthropic_api_key="", tavily_api_key="",
        **overrides,
    )


@asynccontextmanager
async def client_for(search_results=None, delay=0.0, with_context=True, **settings_overrides):
    if search_results is None:
        search_results = {"a": [source(1)]}
    context = (
        AgentContext(llm=FakeLLM(RESPONSES), search=FakeSearch(search_results, delay))
        if with_context
        else None
    )
    app = create_app(settings(**settings_overrides), context=context)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


async def read_events(client, run_id, headers=None) -> list[tuple[int, dict]]:
    events = []
    async with client.stream("GET", f"/api/runs/{run_id}/events", headers=headers) as response:
        assert response.headers["content-type"].startswith("text/event-stream")
        seq = None
        async for line in response.aiter_lines():
            if line.startswith("id: "):
                seq = int(line[4:])
            elif line.startswith("data: "):
                events.append((seq, json.loads(line[6:])))
    return events


async def test_run_streams_progress_and_persists_report():
    async with client_for(delay=0.05) as client:
        response = await client.post("/api/runs", json={"question": "  Is   coffee healthy? "})
        assert response.status_code == 201
        run = response.json()
        assert run["status"] == "running"
        assert run["question"] == "Is coffee healthy?"

        events = await read_events(client, run["id"])
        types = [e["type"] for _, e in events]
        assert types[0] == "run_started"
        assert "plan_ready" in types and "sources_evaluated" in types
        assert types[-1] == "report_ready"
        assert [seq for seq, _ in events] == list(range(1, len(events) + 1))

        stored = (await client.get(f"/api/runs/{run['id']}")).json()
        assert stored["status"] == "completed"
        assert stored["title"] == "The answer"
        assert stored["report"]["sources"][0]["domain"] == "example.com"

        history = (await client.get("/api/runs")).json()
        assert [r["id"] for r in history] == [run["id"]]
        assert history[0]["report"] is None  # list view stays light


async def test_reconnect_resumes_after_last_event_id():
    async with client_for() as client:
        run = (await client.post("/api/runs", json={"question": "question"})).json()
        everything = await read_events(client, run["id"])
        resumed = await read_events(client, run["id"], headers={"Last-Event-ID": "3"})
        assert resumed == everything[3:]


async def test_failed_run_reports_error():
    async with client_for(search_results={}) as client:
        run = (await client.post("/api/runs", json={"question": "question"})).json()
        events = await read_events(client, run["id"])
        assert events[-1][1]["type"] == "run_failed"
        assert "No usable evidence" in events[-1][1]["error"]
        assert (await client.get(f"/api/runs/{run['id']}")).json()["status"] == "failed"


async def test_concurrency_limit():
    async with client_for(delay=0.3, max_concurrent_runs=1) as client:
        assert (await client.post("/api/runs", json={"question": "first"})).status_code == 201
        second = await client.post("/api/runs", json={"question": "second"})
        assert second.status_code == 429


async def test_validation_not_found_and_delete():
    async with client_for() as client:
        assert (await client.post("/api/runs", json={"question": "x"})).status_code == 422
        assert (await client.get("/api/runs/missing")).status_code == 404

        run = (await client.post("/api/runs", json={"question": "question"})).json()
        assert (await client.delete(f"/api/runs/{run['id']}")).status_code == 409
        await read_events(client, run["id"])  # wait for completion
        assert (await client.delete(f"/api/runs/{run['id']}")).status_code == 204
        assert (await client.get(f"/api/runs/{run['id']}")).status_code == 404


async def test_without_api_keys_history_works_but_runs_are_disabled():
    async with client_for(with_context=False) as client:
        health = (await client.get("/api/health")).json()
        assert health["configured"] is False and health["demo"] is False
        # Without a Tavily key the web provider is unavailable; the keyless ones remain.
        assert health["providers"] == ["academic", "reference"]
        assert (await client.get("/api/runs")).json() == []
        assert (await client.post("/api/runs", json={"question": "question"})).status_code == 503


async def test_store_marks_interrupted_runs_failed():
    store = RunStore(":memory:")
    await store.create_run("r1", "q")
    assert await store.fail_interrupted_runs() == 1
    run = await store.get_run("r1")
    assert run.status == "failed" and "restart" in run.error
    store.close()


async def test_demo_mode_runs_the_real_graph_without_keys(monkeypatch):
    monkeypatch.setattr("app.demo._DELAYS", {})
    monkeypatch.setattr("app.demo.asyncio.sleep", _no_sleep)
    app = create_app(settings(demo_mode=True))
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            assert (await client.get("/api/health")).json()["demo"] is True
            run = (await client.post("/api/runs", json={"question": "Does demo mode work?"})).json()
            events = await read_events(client, run["id"])
            assert events[-1][1]["type"] == "report_ready"
            report = events[-1][1]["report"]
            assert report["title"].startswith("Demo report")
            assert report["sources"] and report["conflicts"]


async def _no_sleep(_seconds):
    return None


@pytest.fixture(autouse=True)
def quiet_logs(caplog):
    caplog.set_level("ERROR")


async def test_cancel_stops_a_running_run():
    async with client_for(delay=0.5) as client:
        run = (await client.post("/api/runs", json={"question": "question"})).json()
        assert (await client.post(f"/api/runs/{run['id']}/cancel")).status_code == 202
        events = await read_events(client, run["id"])
        assert events[-1][1] == {
            "type": "run_failed",
            "error": "Stopped by user.",
            "usage": {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0},
        }
        assert (await client.post(f"/api/runs/{run['id']}/cancel")).status_code == 409


async def test_rate_limit_per_client():
    async with client_for(runs_per_hour_per_client=2) as client:
        for _ in range(2):
            run = (await client.post("/api/runs", json={"question": "question"})).json()
            await read_events(client, run["id"])
        blocked = await client.post("/api/runs", json={"question": "question"})
        assert blocked.status_code == 429
        assert int(blocked.headers["retry-after"]) > 0


async def test_report_carries_metrics_and_run_records_usage():
    async with client_for() as client:
        run = (await client.post("/api/runs", json={"question": "question"})).json()
        events = await read_events(client, run["id"])
        final = events[-1][1]
        metrics = final["report"]["metrics"]
        assert metrics["sources_cited"] == 1 and metrics["evidence_items"] == 1
        assert metrics["verified_quotes"] == 1 and metrics["verified_rate"] == 1.0
        assert metrics["providers"] == {"web": 1}
        assert "usage" in final
        stored = (await client.get(f"/api/runs/{run['id']}")).json()
        assert stored["usage"] == final["usage"]


async def test_store_migrates_databases_from_before_usage_tracking(tmp_path):
    import sqlite3

    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE runs (id TEXT PRIMARY KEY, question TEXT NOT NULL, status TEXT NOT NULL, "
        "title TEXT, report TEXT, error TEXT, created_at TEXT NOT NULL, completed_at TEXT)"
    )
    conn.execute("INSERT INTO runs (id, question, status, created_at) VALUES ('r1', 'q', 'completed', 'now')")
    conn.commit()
    conn.close()

    store = RunStore(str(path))
    await store.complete_run("r1", {"title": "t"}, {"calls": 3})
    assert (await store.get_run("r1")).usage == {"calls": 3}
    store.close()


async def test_stream_does_not_miss_a_final_event_racing_with_completion():
    """Regression: the run finishing between reading events and checking it is active."""
    import asyncio

    from app.api.runs import RunManager

    store = RunStore(":memory:")
    await store.create_run("r1", "q")
    manager = RunManager(store, context=None, graph=None)
    manager._signals["r1"] = asyncio.Condition()
    await store.append_event("r1", {"type": "run_started"})

    real_events_after = store.events_after

    async def events_after_then_finish(run_id, after_seq=0):
        events = await real_events_after(run_id, after_seq)
        if after_seq == 0:
            # Worst-case interleaving: the run stores its final event and
            # deactivates right after the stream's read.
            await store.append_event("r1", {"type": "report_ready"})
            manager._signals.pop("r1")
        return events

    store.events_after = events_after_then_finish
    seen = [e.data["type"] async for e in manager.events("r1") if e]
    assert seen == ["run_started", "report_ready"]
    store.close()
