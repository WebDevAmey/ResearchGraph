from app.agent.context import AgentContext
from app.agent.graph import build_graph
from app.agent.nodes.conflicts import resolve_conflicts
from app.agent.schemas import (
    ConflictAnalysis,
    ConflictFinding,
    ConflictSide,
    Evidence,
    KeyPoint,
    ReportDraft,
    ResearchPlan,
    SourceEvaluation,
    Topic,
    TopicAnalysis,
)
from tests.fakes import APPROVE_ALL, FakeLLM, FakeSearch, source


def evidence(n: int) -> Evidence:
    return Evidence(
        statement=f"claim {n}", quote="q", quote_verified=True,
        source_urls=[f"https://example.com/{n}"],
    )


def finding(*sides: list[int]) -> ConflictFinding:
    return ConflictFinding(
        question="Does X work?",
        sides=[ConflictSide(stance=f"side {i}", evidence_ids=ids) for i, ids in enumerate(sides)],
        explanation="Different populations.",
        verdict="Unresolved.",
    )


def test_resolve_maps_evidence_numbers_to_sources():
    conflicts = resolve_conflicts(ConflictAnalysis(conflicts=[finding([1], [2, 3])]), [
        evidence(1), evidence(2), evidence(3)
    ])
    assert [p.source_urls for p in conflicts[0].positions] == [
        ["https://example.com/1"],
        ["https://example.com/2", "https://example.com/3"],
    ]


def test_conflicts_need_two_grounded_sides():
    analysis = ConflictAnalysis(conflicts=[finding([1], [99]), finding([1])])
    assert resolve_conflicts(analysis, [evidence(1)]) == []


# --- In the graph -------------------------------------------------------------

PLAN = ResearchPlan(
    time_sensitive=False, understanding="u",
    topics=[
        Topic(title="A", question="qa", search_queries=["a"]),
        Topic(title="B", question="qb", search_queries=["b"]),
    ],
)
DRAFT = ReportDraft(
    title="t", executive_summary="e [1]", key_findings=["f"], detailed_analysis="d",
    conflicting_evidence="Sources disagree.", limitations="l", conclusion="c",
)


def analysis_for(variables):
    # Each topic's single source is cited as [1] within that topic.
    return TopicAnalysis(
        summary="s", key_points=[KeyPoint(statement="claim", quote="Content", source_ids=[1])]
    )


def make(conflicts):
    llm = FakeLLM({
        ResearchPlan: PLAN,
        SourceEvaluation: APPROVE_ALL,
        TopicAnalysis: analysis_for,
        ConflictAnalysis: conflicts,
        ReportDraft: DRAFT,
    })
    search = FakeSearch({"a": [source(1)], "b": [source(2)]})
    return AgentContext(llm=llm, search=search), llm


async def test_conflicts_reach_the_report_with_citations():
    context, llm = make(ConflictAnalysis(conflicts=[finding([1], [2])]))
    state = await build_graph().ainvoke({"question": "q"}, context=context)

    report = state["report"]
    assert len(report.conflicts) == 1
    cited = {i for p in report.conflicts[0].positions for i in p.source_ids}
    # Source 2 is cited only by the conflict, yet still listed in the report.
    assert cited <= {s.id for s in report.sources}
    assert len(report.sources) == 2
    assert "Does X work?" in llm.calls_for(ReportDraft)[0]["conflicts"]


async def test_conflict_detection_failure_does_not_fail_the_run():
    context, _ = make(RuntimeError("model down"))
    state = await build_graph().ainvoke({"question": "q"}, context=context)
    assert state["conflicts"] == []
    assert state["report"].conflicts == []


async def test_detection_is_skipped_with_a_single_source():
    llm = FakeLLM({
        ResearchPlan: ResearchPlan(time_sensitive=False, understanding="u", topics=[PLAN.topics[0]]),
        SourceEvaluation: APPROVE_ALL,
        TopicAnalysis: analysis_for,
        ReportDraft: DRAFT,
    })
    context = AgentContext(llm=llm, search=FakeSearch({"a": [source(1)]}))
    state = await build_graph().ainvoke({"question": "q"}, context=context)
    assert llm.calls_for(ConflictAnalysis) == []
    assert state["conflicts"] == []
