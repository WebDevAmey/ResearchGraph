from datetime import date

from langgraph.runtime import Runtime
from langgraph.types import Send

from app.agent.context import AgentContext
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
    return {"plan": plan.model_copy(update={"topics": topics})}


def dispatch_research(state: ResearchState) -> list[Send]:
    """Fan out: one `research_topic` branch per topic, all run in parallel."""
    return [
        Send("research_topic", TopicTask(question=state["question"], topic=topic))
        for topic in state["plan"].topics
    ]
