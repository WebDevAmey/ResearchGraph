"""Demo mode: run the real graph against a scripted LLM and search engine.

Lets you explore the UI with no API keys (DEMO_MODE=true). Every node,
reducer, event, and citation check runs for real; only the two ports are
swapped. All content is placeholder text on example.com, labelled as such.
"""

import asyncio
import hashlib
import random
import re
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from app.agent.context import AgentContext
from app.agent.schemas import (
    ConflictAnalysis,
    ConflictFinding,
    ConflictSide,
    KeyPoint,
    ReportDraft,
    ResearchPlan,
    Source,
    SourceAssessment,
    SourceEvaluation,
    Topic,
    TopicAnalysis,
)

_TOPICS = [
    ("Measured outcomes", "What do controlled studies measure?"),
    ("Expert and institutional views", "What do experts and institutions conclude?"),
    ("Counter-evidence", "What evidence points the other way?"),
    ("Recent developments", "What has changed in the last two years?"),
]
_TYPES = ["academic", "government", "news", "industry", "blog"]
_DELAYS = {
    ResearchPlan: 1.6,
    SourceEvaluation: 1.2,
    TopicAnalysis: 2.2,
    ConflictAnalysis: 1.8,
    ReportDraft: 3.0,
}


class DemoSearch:
    async def search(self, query: str) -> list[Source]:
        await asyncio.sleep(random.uniform(0.6, 1.4))
        # Unique per query so topics don't share (and de-duplicate) the same URLs.
        slug = hashlib.sha1(query.encode()).hexdigest()[:10]
        return [
            Source(
                url=f"https://example.com/demo/{slug}/{i}",
                title=f"Sample source {i}: {query[:60]}",
                content=(
                    f"This is placeholder text standing in for a real web page about {query}. "
                    f"In a live run it would contain the page's extracted content. "
                    f"Sample finding {i}: the measured effect was moderate in the groups studied."
                ),
                score=round(random.uniform(0.4, 0.95), 2),
            )
            for i in range(1, 6)
        ]


class DemoLLM:
    async def generate(
        self,
        prompt: ChatPromptTemplate,
        variables: dict[str, Any],
        schema: type[BaseModel],
        *,
        effort: str | None = None,
    ) -> BaseModel:
        await asyncio.sleep(_DELAYS.get(schema, 1.0) * random.uniform(0.7, 1.3))
        return _RESPONDERS[schema](variables)


def _plan(v: dict) -> ResearchPlan:
    q = v["question"]
    return ResearchPlan(
        understanding=f"Demo run: a sample investigation of “{q}”.",
        topics=[
            Topic(title=title, question=question, search_queries=[f"{q} {title.lower()}"])
            for title, question in _TOPICS
        ],
    )


def _evaluate(v: dict) -> SourceEvaluation:
    count = v["sources"].count("\nURL: ")
    return SourceEvaluation(
        assessments=[
            SourceAssessment(
                source_id=i,
                relevance=random.choice([2, 3, 4, 4, 5, 5]),
                credibility=random.choice([2, 3, 4, 5]),
                source_type=random.choice(_TYPES),
                published_year=random.choice([2023, 2024, 2025, 2026, None]),
                reason="Demo assessment.",
            )
            for i in range(1, count + 1)
        ]
    )


def _analyze(v: dict) -> TopicAnalysis:
    count = v["sources"].count("\nURL: ")
    return TopicAnalysis(
        summary=f"Demo summary for “{v['topic']}”. A live run would synthesise what the sources say here.",
        key_points=[
            KeyPoint(
                statement=f"Sample claim {i} about this topic, supported by the cited source.",
                quote=f"Sample finding {_source_number(v['sources'], i)}: the measured effect was moderate",
                source_ids=[i],
            )
            for i in range(1, min(count, 3) + 1)
        ],
    )


def _conflicts(v: dict) -> ConflictAnalysis:
    count = v["evidence"].count("\n[") + 1
    if count < 2:
        return ConflictAnalysis(conflicts=[])
    return ConflictAnalysis(
        conflicts=[
            ConflictFinding(
                question="How large is the effect? (demo)",
                sides=[
                    ConflictSide(stance="Sample position: the effect is substantial.", evidence_ids=[1]),
                    ConflictSide(stance="Sample position: the effect is negligible.", evidence_ids=[count]),
                ],
                explanation="In a live run, this explains why sources diverge, such as different populations or timeframes.",
                verdict="Demo verdict: the evidence leans towards a moderate effect.",
            )
        ]
    )


def _report(v: dict) -> ReportDraft:
    ids = [int(n) for n in re.findall(r"^\[(\d+)\]", v["sources"], flags=re.M)] or [1]
    c = lambda i: f"[{ids[i % len(ids)]}]"  # noqa: E731
    return ReportDraft(
        title=f"Demo report: {v['question']}",
        executive_summary=(
            "This is a demo report generated from placeholder data, so no conclusions should be "
            f"drawn from it {c(0)}. In a live run, this paragraph answers the question directly "
            f"and cites the strongest evidence {c(1)}{c(2)}."
        ),
        key_findings=[
            f"Sample finding about measured outcomes {c(0)}.",
            f"Sample finding about expert consensus {c(3)}.",
            f"Sample finding about counter-evidence {c(5)}.",
            f"Sample finding about recent developments {c(7)}.",
        ],
        detailed_analysis=(
            "### Measured outcomes\n"
            f"Placeholder analysis of controlled studies, citing sources inline {c(0)}{c(1)}.\n\n"
            "### Expert views\n"
            f"Placeholder analysis of institutional positions {c(3)}.\n\n"
            "### Recent developments\n"
            f"Placeholder analysis of what has changed recently {c(7)}."
        ),
        conflicting_evidence=(
            f"Sample sources disagree on the size of the effect {c(0)}{c(9)}. "
            "A live run explains why and weighs each side."
        ),
        limitations="Demo mode uses placeholder sources; nothing here reflects real research.",
        conclusion=f"Demo conclusion. Connect API keys to run real research {c(2)}.",
    )


def _source_number(sources_text: str, position: int) -> int:
    """The 'Sample finding N' text in the position-th source shown to the model."""
    numbers = re.findall(r"Sample finding (\d+):", sources_text)
    return int(numbers[position - 1]) if position <= len(numbers) else position


_RESPONDERS = {
    ResearchPlan: _plan,
    SourceEvaluation: _evaluate,
    TopicAnalysis: _analyze,
    ConflictAnalysis: _conflicts,
    ReportDraft: _report,
}


def demo_context() -> AgentContext:
    return AgentContext(llm=DemoLLM(), search=DemoSearch())
