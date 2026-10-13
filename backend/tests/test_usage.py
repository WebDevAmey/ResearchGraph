"""Cost tracking: the callback must see model calls made deep inside graph nodes."""

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

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
from app.agent.usage import UsageTracker
from tests.fakes import APPROVE_ALL, FakeLLM, FakeSearch, source


def message(model: str, input_tokens: int, output_tokens: int) -> AIMessage:
    return AIMessage(
        "ok",
        usage_metadata={
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        },
        response_metadata={"model_name": model},
    )


def test_summary_prices_by_model():
    tracker = UsageTracker()
    model = GenericFakeChatModel(messages=iter([
        message("claude-opus-5-5", 1_000_000, 0),
        message("claude-opus-5-5", 0, 100_000),
    ]))
    for _ in range(2):
        model.invoke("x", config={"callbacks": [tracker]})
    summary = tracker.summary()
    assert (summary.calls, summary.input_tokens, summary.output_tokens) == (2, 1_000_000, 100_000)
    assert summary.cost_usd == 4.0 + 2.0  # $4/M input + $20/M output


def test_unknown_model_has_no_cost_estimate():
    tracker = UsageTracker()
    GenericFakeChatModel(messages=iter([message("mystery-model", 10, 10)])).invoke(
        "x", config={"callbacks": [tracker]}
    )
    assert tracker.summary().cost_usd is None


class LangChainBackedLLM(FakeLLM):
    """A fake that, like ClaudeLLM, makes a real LangChain model call per request."""

    def __init__(self, responses):
        super().__init__(responses)
        self.model = GenericFakeChatModel(
            messages=iter([message("claude-opus-5-5", 100, 10) for _ in range(50)])
        )

    async def generate(self, prompt, variables, schema, *, effort=None):
        await self.model.ainvoke("x")  # no config passed: must inherit the graph's callbacks
        return await super().generate(prompt, variables, schema, effort=effort)


async def test_tracker_sees_calls_inside_parallel_subgraphs():
    plan = ResearchPlan(
        time_sensitive=False, understanding="u",
        topics=[Topic(title=t, question=t, search_queries=[t]) for t in ("a", "b")],
    )
    llm = LangChainBackedLLM({
        ResearchPlan: plan,
        SourceEvaluation: APPROVE_ALL,
        TopicAnalysis: TopicAnalysis(
            summary="s", key_points=[KeyPoint(statement="c", quote="Content", source_ids=[1])]
        ),
        ConflictAnalysis: ConflictAnalysis(conflicts=[]),
        ReportDraft: ReportDraft(
            title="t", executive_summary="e [1]", key_findings=[], detailed_analysis="d",
            conflicting_evidence="n", limitations="l", conclusion="c",
        ),
    })
    context = AgentContext(llm=llm, search=FakeSearch({"a": [source(1)], "b": [source(2)]}))
    tracker = UsageTracker()
    await build_graph().ainvoke({"question": "q"}, config={"callbacks": [tracker]}, context=context)

    # plan + 2×evaluate + 2×analyze + conflicts + synthesis
    assert tracker.summary().calls == len(llm.calls) == 7
    assert tracker.summary().input_tokens == 700
