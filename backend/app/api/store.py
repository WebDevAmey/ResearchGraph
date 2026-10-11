"""SQLite persistence for runs and their event logs.

A run's events are the source of truth for the UI: the timeline, source
cards, and final report are all rebuilt by replaying them. That makes
reconnects, page refreshes, and history views the same code path.

sqlite3 is synchronous, so every call runs in a worker thread. One shared
connection guarded by a lock is plenty for a single-process app.
"""

import asyncio
import json
import sqlite3
import threading
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel

RunStatus = Literal["running", "completed", "failed"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id           TEXT PRIMARY KEY,
    question     TEXT NOT NULL,
    status       TEXT NOT NULL,
    title        TEXT,
    report       TEXT,
    error        TEXT,
    created_at   TEXT NOT NULL,
    completed_at TEXT
);
CREATE TABLE IF NOT EXISTS events (
    run_id TEXT    NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    seq    INTEGER NOT NULL,
    data   TEXT    NOT NULL,
    PRIMARY KEY (run_id, seq)
);
CREATE INDEX IF NOT EXISTS runs_created ON runs(created_at DESC);
"""


class RunRecord(BaseModel):
    id: str
    question: str
    status: RunStatus
    title: str | None = None
    report: dict[str, Any] | None = None
    error: str | None = None
    created_at: str
    completed_at: str | None = None


class StoredEvent(BaseModel):
    seq: int
    data: dict[str, Any]


class RunStore:
    def __init__(self, path: str) -> None:
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.executescript(_SCHEMA)

    async def _run(self, fn, *args):
        def locked():
            with self._lock, self._conn:
                return fn(*args)

        return await asyncio.to_thread(locked)

    # --- runs ---------------------------------------------------------------

    async def create_run(self, run_id: str, question: str) -> RunRecord:
        now = _now()
        await self._run(
            lambda: self._conn.execute(
                "INSERT INTO runs (id, question, status, created_at) VALUES (?, ?, 'running', ?)",
                (run_id, question, now),
            )
        )
        return RunRecord(id=run_id, question=question, status="running", created_at=now)

    async def complete_run(self, run_id: str, report: dict[str, Any]) -> None:
        await self._run(
            lambda: self._conn.execute(
                "UPDATE runs SET status='completed', title=?, report=?, completed_at=? WHERE id=?",
                (report.get("title"), json.dumps(report), _now(), run_id),
            )
        )

    async def fail_run(self, run_id: str, error: str) -> None:
        await self._run(
            lambda: self._conn.execute(
                "UPDATE runs SET status='failed', error=?, completed_at=? WHERE id=?",
                (error, _now(), run_id),
            )
        )

    async def fail_interrupted_runs(self) -> int:
        """Runs still 'running' at startup were cut off by a restart."""
        cursor = await self._run(
            lambda: self._conn.execute(
                "UPDATE runs SET status='failed', error=?, completed_at=? WHERE status='running'",
                ("Interrupted by a server restart.", _now()),
            )
        )
        return cursor.rowcount

    async def get_run(self, run_id: str) -> RunRecord | None:
        row = await self._run(
            lambda: self._conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        )
        return _to_record(row) if row else None

    async def list_runs(self, limit: int = 20) -> list[RunRecord]:
        rows = await self._run(
            lambda: self._conn.execute(
                "SELECT id, question, status, title, error, created_at, completed_at "
                "FROM runs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        )
        return [_to_record(r) for r in rows]

    async def delete_run(self, run_id: str) -> bool:
        cursor = await self._run(
            lambda: self._conn.execute("DELETE FROM runs WHERE id=?", (run_id,))
        )
        return cursor.rowcount > 0

    # --- events -------------------------------------------------------------

    async def append_event(self, run_id: str, data: dict[str, Any]) -> int:
        def insert():
            (seq,) = self._conn.execute(
                "SELECT COALESCE(MAX(seq), 0) + 1 FROM events WHERE run_id=?", (run_id,)
            ).fetchone()
            self._conn.execute(
                "INSERT INTO events (run_id, seq, data) VALUES (?, ?, ?)",
                (run_id, seq, json.dumps(data)),
            )
            return seq

        return await self._run(insert)

    async def events_after(self, run_id: str, after_seq: int = 0) -> list[StoredEvent]:
        rows = await self._run(
            lambda: self._conn.execute(
                "SELECT seq, data FROM events WHERE run_id=? AND seq>? ORDER BY seq",
                (run_id, after_seq),
            ).fetchall()
        )
        return [StoredEvent(seq=r["seq"], data=json.loads(r["data"])) for r in rows]

    def close(self) -> None:
        with self._lock:
            self._conn.close()


def _to_record(row: sqlite3.Row) -> RunRecord:
    data = dict(row)
    if data.get("report"):
        data["report"] = json.loads(data["report"])
    return RunRecord(**data)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
