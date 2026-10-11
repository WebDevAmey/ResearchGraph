"""The research graph.

Parent graph:

    START → plan_research ─┬─► research_topic ─┐
                           ├─► research_topic ─┼─► detect_conflicts → synthesize_report → END
                           └─► research_topic ─┘
                     (one branch per topic, via Send)

Each `research_topic` branch is a subgraph:

    START → search_sources → evaluate_sources → analyze_topic → finalize_topic → END
                 │                  │                                ▲
                 └── no sources ────┴── none pass review ────────────┘
"""

from langgraph.graph import END, START, StateGraph

from app.agent.context import AgentContext
from app.agent.nodes.conflicts import detect_conflicts
from app.agent.nodes.evaluator import evaluate_sources
from app.agent.nodes.planner import dispatch_research, plan_research
from app.agent.nodes.researcher import analyze_topic, finalize_topic, search_sources
from app.agent.nodes.synthesizer import synthesize_report
from app.agent.state import ResearchInput, ResearchState, TopicOutput, TopicState, TopicTask


def build_research_subgraph():
    builder = StateGraph(
        TopicState, context_schema=AgentContext, input_schema=TopicTask, output_schema=TopicOutput
    )

    builder.add_node("search_sources", search_sources)
    builder.add_node("evaluate_sources", evaluate_sources)
    builder.add_node("analyze_topic", analyze_topic)
    builder.add_node("finalize_topic", finalize_topic)

    builder.add_edge(START, "search_sources")
    builder.add_conditional_edges(
        "search_sources",
        lambda s: "evaluate_sources" if s.get("candidates") else "finalize_topic",
        ["evaluate_sources", "finalize_topic"],
    )
    builder.add_conditional_edges(
        "evaluate_sources",
        lambda s: "analyze_topic" if s.get("sources") else "finalize_topic",
        ["analyze_topic", "finalize_topic"],
    )
    builder.add_edge("analyze_topic", "finalize_topic")
    builder.add_edge("finalize_topic", END)

    return builder.compile()


def build_graph():
    builder = StateGraph(ResearchState, context_schema=AgentContext, input_schema=ResearchInput)

    builder.add_node("plan_research", plan_research)
    builder.add_node("research_topic", build_research_subgraph())
    builder.add_node("detect_conflicts", detect_conflicts)
    builder.add_node("synthesize_report", synthesize_report)

    builder.add_edge(START, "plan_research")
    builder.add_conditional_edges("plan_research", dispatch_research, ["research_topic"])
    builder.add_edge("research_topic", "detect_conflicts")
    builder.add_edge("detect_conflicts", "synthesize_report")
    builder.add_edge("synthesize_report", END)

    return builder.compile()


graph = build_graph()
