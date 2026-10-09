"""The research graph.

    START → plan_research ─┬─► research_topic ─┐
                           ├─► research_topic ─┼─► synthesize_report → END
                           └─► research_topic ─┘
                     (one branch per topic, via Send)
"""

from langgraph.graph import END, START, StateGraph

from app.agent.context import AgentContext
from app.agent.nodes.planner import dispatch_research, plan_research
from app.agent.nodes.researcher import research_topic
from app.agent.nodes.synthesizer import synthesize_report
from app.agent.state import ResearchInput, ResearchState


def build_graph():
    builder = StateGraph(ResearchState, context_schema=AgentContext, input_schema=ResearchInput)

    builder.add_node("plan_research", plan_research)
    builder.add_node("research_topic", research_topic)
    builder.add_node("synthesize_report", synthesize_report)

    builder.add_edge(START, "plan_research")
    builder.add_conditional_edges("plan_research", dispatch_research, ["research_topic"])
    builder.add_edge("research_topic", "synthesize_report")
    builder.add_edge("synthesize_report", END)

    return builder.compile()


graph = build_graph()
