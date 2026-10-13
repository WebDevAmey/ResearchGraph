"""Run a research question from the terminal, showing each step as it completes.

    python -m app.cli "What is the evidence that remote work affects productivity?"
"""

import argparse
import asyncio
import sys
from pathlib import Path

from app.agent.context import context_from_settings
from app.agent.graph import graph
from app.agent.nodes.synthesizer import InsufficientEvidenceError
from app.agent.usage import UsageTracker
from app.config import configure_tracing, get_settings


async def run(question: str, out: Path | None) -> int:
    settings = get_settings()
    if not settings.can_research:
        print("Set ANTHROPIC_API_KEY (and optionally TAVILY_API_KEY) in .env; see .env.example")
        return 1
    configure_tracing(settings)

    context = context_from_settings(settings)
    usage = UsageTracker()
    report = None
    try:
        # stream_mode="updates" yields {node_name: state_update} as each node finishes.
        async for update in graph.astream(
            {"question": question},
            config={"callbacks": [usage]},
            context=context,
            stream_mode="updates",
        ):
            for node, data in update.items():
                if node == "plan_research":
                    plan = data["plan"]
                    print(f"✓ Plan: {plan.understanding}")
                    for topic in plan.topics:
                        print(f"  · {topic.title}")
                elif node == "research_topic":
                    result = data["topic_results"][0]
                    reviewed = len(result.sources) + len(result.rejected_sources)
                    status = (
                        f"✗ {result.error}"
                        if result.error
                        else f"{len(result.evidence)} evidence items from "
                        f"{len(result.sources)}/{reviewed} sources that passed review"
                    )
                    print(f"✓ Researched '{result.topic.title}': {status}")
                elif node == "detect_conflicts":
                    print(f"✓ Cross-checked evidence: {len(data['conflicts'])} conflicts found")
                elif node == "synthesize_report":
                    report = data["report"]
                    cost = usage.summary()
                    price = f" · ${cost.cost_usd:.2f}" if cost.cost_usd is not None else ""
                    print(
                        f"✓ Report written · {cost.calls} model calls · "
                        f"{cost.input_tokens + cost.output_tokens:,} tokens{price}\n"
                    )
    except InsufficientEvidenceError as exc:
        print(f"✗ {exc}")
        return 1

    markdown = report.to_markdown()
    if out:
        out.write_text(markdown)
        print(f"Saved to {out}")
    else:
        print(markdown)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="ResearchGraph: evidence-backed research.")
    parser.add_argument("question")
    parser.add_argument("--out", type=Path, help="Write the report to a Markdown file.")
    args = parser.parse_args()
    sys.exit(asyncio.run(run(args.question, args.out)))


if __name__ == "__main__":
    main()
