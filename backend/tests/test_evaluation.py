from app.agent.context import AgentContext
from app.agent.graph import build_graph
from app.agent.nodes.evaluator import select_sources
from app.agent.schemas import (
    KeyPoint,
    ReportDraft,
    ResearchPlan,
    SourceEvaluation,
    Topic,
    TopicAnalysis,
)
from tests.fakes import APPROVE_ALL, FakeLLM, FakeSearch, assessment, source

# --- The selection rule (pure function) --------------------------------------


def test_rejects_low_relevance_and_low_credibility():
    candidates = [source(1), source(2), source(3)]
    kept, rejected = select_sources(
        candidates,
        [assessment(1), assessment(2, relevance=2), assessment(3, credibility=1)],
        limit=10,
    )
    assert [s.url for s in kept] == [candidates[0].url]
    assert len(rejected) == 2
    assert all(s.assessment for s in rejected)


def test_ranks_by_quality_and_applies_cap():
    candidates = [source(1), source(2), source(3)]
    kept, rejected = select_sources(
        candidates,
        [assessment(1, 3, 3), assessment(2, 5, 5), assessment(3, 4, 4)],
        limit=2,
    )
    assert [s.title for s in kept] == ["Source 2", "Source 3"]
    assert [s.title for s in rejected] == ["Source 1"]
    assert kept[0].assessment.quality == 1.0


def test_unassessed_sources_are_rejected_and_unknown_ids_ignored():
    candidates = [source(1), source(2)]
    kept, rejected = select_sources(candidates, [assessment(1), assessment(7)], limit=10)
    assert [s.title for s in kept] == ["Source 1"]
    assert rejected[0].assessment is None


def test_out_of_range_scores_are_clamped():
    kept, _ = select_sources([source(1)], [assessment(1, relevance=9, credibility=0)], limit=10)
    assert kept == []  # credibility 0 clamps to 1, below the threshold


# --- Evaluation inside the graph ---------------------------------------------

PLAN = ResearchPlan(
    understanding="u",
    topics=[
        Topic(title="A", question="qa", search_queries=["a"]),
        Topic(title="B", question="qb", search_queries=["b"]),
    ],
)
ANALYSIS = TopicAnalysis(summary="s", key_points=[KeyPoint(statement="claim", source_ids=[1])])
DRAFT = ReportDraft(
    title="t",
    executive_summary="e [1]",
    key_findings=["f [1]"],
    detailed_analysis="d",
    limitations="l",
    conclusion="c",
)


def run_with(evaluation, search_results):
    llm = FakeLLM(
        {
            ResearchPlan: PLAN,
            SourceEvaluation: evaluation,
            TopicAnalysis: ANALYSIS,
            ReportDraft: DRAFT,
        }
    )
    context = AgentContext(llm=llm, search=FakeSearch(search_results), max_sources_per_topic=6)
    return build_graph().ainvoke({"question": "q"}, context=context), llm


async def test_analyzer_only_sees_sources_that_passed():
    evaluation = SourceEvaluation(assessments=[assessment(1), assessment(2, relevance=1)])
    run, llm = run_with(evaluation, {"a": [source(1), source(2)], "b": [source(3)]})
    state = await run

    for variables in llm.calls_for(TopicAnalysis):
        assert "example.com/2" not in variables["sources"]
    topic_a = next(r for r in state["topic_results"] if r.topic.title == "A")
    assert [s.title for s in topic_a.rejected_sources] == ["Source 2"]


async def test_evaluation_runs_at_low_effort():
    run, llm = run_with(APPROVE_ALL, {"a": [source(1)], "b": [source(2)]})
    await run
    assert llm.efforts_for(SourceEvaluation) == ["low", "low"]
    assert llm.efforts_for(TopicAnalysis) == [None, None]


async def test_evaluation_failure_falls_back_to_search_ranking():
    run, _ = run_with(
        RuntimeError("model down"),
        {"a": [source(1, score=0.2), source(2, score=0.9)], "b": [source(3)]},
    )
    state = await run
    topic_a = next(r for r in state["topic_results"] if r.topic.title == "A")
    assert [s.title for s in topic_a.sources] == ["Source 2", "Source 1"]
    assert "report" in state


async def test_topic_with_no_passing_sources_reports_error_but_run_continues():
    def reject_topic_a(variables):
        if variables["topic"] == "qa":
            return SourceEvaluation(assessments=[assessment(1, relevance=1)])
        return APPROVE_ALL

    run, llm = run_with(reject_topic_a, {"a": [source(1)], "b": [source(2)]})
    state = await run
    topic_a = next(r for r in state["topic_results"] if r.topic.title == "A")
    assert topic_a.error == "No sources passed quality review."
    assert len(llm.calls_for(TopicAnalysis)) == 1  # only topic B was analysed
    assert state["report"].sources[0].assessment.source_type == "news"
