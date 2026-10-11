"""Progress events streamed with stream_mode="custom", including from subgraphs."""

import json

from app.agent.context import AgentContext
from app.agent.graph import build_graph
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
    understanding="u",
    topics=[
        Topic(title="A", question="qa", search_queries=["a"]),
        Topic(title="B", question="qb", search_queries=["b"]),
    ],
)


async def collect_events():
    llm = FakeLLM({
        ResearchPlan: PLAN,
        SourceEvaluation: APPROVE_ALL,
        TopicAnalysis: TopicAnalysis(
            summary="s", key_points=[KeyPoint(statement="c", quote="Content", source_ids=[1])]
        ),
        ConflictAnalysis: ConflictAnalysis(conflicts=[]),
        ReportDraft: ReportDraft(
            title="t", executive_summary="e [1]", key_findings=[], detailed_analysis="d",
            conflicting_evidence="none", limitations="l", conclusion="c",
        ),
    })
    context = AgentContext(llm=llm, search=FakeSearch({"a": [source(1)], "b": [source(2)]}))
    events = []
    async for _, event in build_graph().astream(
        {"question": "q"}, context=context, stream_mode="custom", subgraphs=True
    ):
        events.append(event)
    return events


async def test_event_sequence():
    events = await collect_events()
    types = [e["type"] for e in events]

    assert types[0] == "plan_ready"
    assert types[-1] == "synthesis_started"
    for topic_id in ("t1", "t2"):
        per_topic = [e["type"] for e in events if e.get("topic_id") == topic_id]
        assert per_topic == ["topic_started", "sources_found", "sources_evaluated", "topic_completed"]
    assert types.index("conflicts_started") > max(
        i for i, t in enumerate(types) if t == "topic_completed"
    )


async def test_events_are_json_serialisable_and_carry_ui_data():
    events = await collect_events()
    json.dumps(events)

    plan = events[0]
    assert [t["id"] for t in plan["topics"]] == ["t1", "t2"]
    evaluated = next(e for e in events if e["type"] == "sources_evaluated")
    card = evaluated["kept"][0]
    assert card["domain"] == "example.com"
    assert card["assessment"]["source_type"] == "news"
