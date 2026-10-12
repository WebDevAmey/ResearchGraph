from datetime import date

from langgraph.runtime import Runtime
from langgraph.types import Send

from app.agent.context import AgentContext
from app.agent.events import emit
from app.agent.prompts import PLANNER_PROMPT
from app.agent.schemas import ResearchPlan, Topic
from app.agent.state import ResearchState, TopicTask


async def plan_research(state: ResearchState, runtime: Runtime[AgentContext]) -> dict:
    ctx = runtime.context
    question = state["question"]
    plan = await ctx.llm.generate(
        PLANNER_PROMPT,
        {"question": question, "max_topics": ctx.max_topics, "today": date.today().isoformat()},
        ResearchPlan,
    )

    topics = [t for t in plan.topics if t.search_queries][: ctx.max_topics]
    if not topics:
        # A plan with nothing to search is useless; research the question as-is.
        topics = [Topic(title="Overview", question=question, search_queries=[question])]
    plan = plan.model_copy(update={"topics": topics})

    emit(
        runtime,
        "plan_ready",
        understanding=plan.understanding,
        time_sensitive=plan.time_sensitive,
        topics=[{"id": topic_id(i), **t.model_dump()} for i, t in enumerate(topics)],
    )
    return {"plan": plan}


def dispatch_research(state: ResearchState) -> list[Send]:
    """Fan out: one `research_topic` branch per topic, all run in parallel."""
    return [
        Send(
            "research_topic",
            TopicTask(
                question=state["question"],
                topic_id=topic_id(i),
                topic=topic,
                time_sensitive=state["plan"].time_sensitive,
            ),
        )
        for i, topic in enumerate(state["plan"].topics)
    ]


def topic_id(index: int) -> str:
    return f"t{index + 1}"
