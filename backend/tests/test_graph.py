import pytest

from app.agent.context import AgentContext
from app.agent.graph import build_graph
from app.agent.nodes.synthesizer import InsufficientEvidenceError
from app.agent.schemas import (
    KeyPoint,
    ReportDraft,
    ResearchPlan,
    SourceEvaluation,
    Topic,
    TopicAnalysis,
)
from tests.fakes import APPROVE_ALL, FakeLLM, FakeSearch, source

QUESTION = "Does remote work affect productivity?"

PLAN = ResearchPlan(
    understanding="Effect of remote work on productivity.",
    topics=[
        Topic(title="Output studies", question="What do studies find?", search_queries=["q1", "q2"]),
        Topic(title="Employer views", question="What do employers report?", search_queries=["q3"]),
    ],
)

ANALYSIS = TopicAnalysis(
    summary="Sources broadly agree.",
    key_points=[
        KeyPoint(statement="Supported claim", source_ids=[1]),
        KeyPoint(statement="Claim citing a non-existent source", source_ids=[42]),
    ],
)

DRAFT = ReportDraft(
    title="Remote work and productivity",
    executive_summary="Mixed evidence [1][2].",
    key_findings=["Finding [1]", "Invented citation [99]"],
    detailed_analysis="### Theme\nDetail [2].",
    limitations="Few long-term studies.",
    conclusion="It depends [1].",
)


DEFAULT_RESPONSES = {
    ResearchPlan: PLAN,
    SourceEvaluation: APPROVE_ALL,
    TopicAnalysis: ANALYSIS,
    ReportDraft: DRAFT,
}


def make_context(search_results, llm_responses=None, max_topics=5):
    llm = FakeLLM({**DEFAULT_RESPONSES, **(llm_responses or {})})
    search = FakeSearch(search_results)
    return AgentContext(llm=llm, search=search, max_topics=max_topics), llm, search


async def run(context):
    return await build_graph().ainvoke({"question": QUESTION}, context=context)


async def test_end_to_end_produces_cited_report():
    context, llm, search = make_context(
        {"q1": [source(1), source(2)], "q2": [source(2)], "q3": [source(3)]}
    )
    state = await run(context)

    # One research branch per topic, merged by the reducer.
    assert {r.topic.title for r in state["topic_results"]} == {"Output studies", "Employer views"}
    # Synthesis runs exactly once, after all branches finish.
    assert len(llm.calls_for(ReportDraft)) == 1

    report = state["report"]
    assert "[99]" not in report.key_findings[1]
    assert [s.id for s in report.sources] == [1, 2]
    assert report.sources[0].url == "https://example.com/1"


async def test_topics_are_researched_in_parallel():
    context, _, search = make_context({"q1": [source(1)], "q2": [source(2)], "q3": [source(3)]})
    await run(context)
    assert search.max_in_flight == 3


async def test_uncited_claims_are_dropped_and_duplicate_sources_merged():
    context, _, _ = make_context({"q1": [source(1), source(2)], "q2": [source(2)], "q3": [source(3)]})
    state = await run(context)
    studies = next(r for r in state["topic_results"] if r.topic.title == "Output studies")
    assert [f.statement for f in studies.findings] == ["Supported claim"]
    assert len(studies.sources) == 2


async def test_failed_search_does_not_sink_the_run():
    context, _, _ = make_context(
        {"q1": RuntimeError("boom"), "q2": RuntimeError("boom"), "q3": [source(3)]}
    )
    state = await run(context)
    studies = next(r for r in state["topic_results"] if r.topic.title == "Output studies")
    assert studies.error == "No sources found."
    assert state["report"].title == DRAFT.title


async def test_plan_is_capped_at_max_topics():
    context, llm, _ = make_context({"q1": [source(1)]}, max_topics=1)
    state = await run(context)
    assert len(state["plan"].topics) == 1
    assert len(llm.calls_for(TopicAnalysis)) == 1


async def test_empty_plan_falls_back_to_the_question_itself():
    empty = ResearchPlan(understanding="?", topics=[])
    context, _, _ = make_context({QUESTION: [source(1)]}, {ResearchPlan: empty})
    state = await run(context)
    assert state["plan"].topics[0].search_queries == [QUESTION]
    assert "report" in state


async def test_no_evidence_raises():
    context, _, _ = make_context({})
    with pytest.raises(InsufficientEvidenceError):
        await run(context)
