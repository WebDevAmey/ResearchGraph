"""Progress events nodes emit while they work.

Nodes call `emit(runtime, "event_type", **data)`. When the graph is streamed
with `stream_mode="custom"`, each call surfaces as one chunk; otherwise it is
a no-op. Payloads must be JSON-serialisable: they go straight to the browser.

Event types, in the order a run produces them:
    plan_ready          {understanding, topics: [{id, title, question, search_queries}]}
    topic_started       {topic_id}
    sources_found       {topic_id, count}
    sources_evaluated   {topic_id, kept: [source], rejected: int}
    topic_completed     {topic_id, summary, evidence_count, error}
    conflicts_started   {}
    conflicts_ready     {count}
    synthesis_started   {}
The API layer adds run_started, report_ready, and run_failed around these.
"""

from typing import Any

from langgraph.runtime import Runtime

from app.agent.schemas import Source

SNIPPET_CHARS = 280


def emit(runtime: Runtime, event_type: str, **data: Any) -> None:
    runtime.stream_writer({"type": event_type, **data})


def source_payload(source: Source) -> dict[str, Any]:
    return {
        "url": source.url,
        "title": source.title,
        "domain": source.domain,
        "snippet": source.content[:SNIPPET_CHARS],
        "assessment": source.assessment.model_dump() if source.assessment else None,
    }
