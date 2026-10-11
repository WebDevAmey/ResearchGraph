"""Shared graph state.

Every node receives the current state and returns a *partial update*.
LangGraph merges updates into the state using each key's reducer:
- keys without a reducer are overwritten by the latest write;
- `topic_results` uses `operator.add`, so parallel research branches
  each append their result instead of clobbering each other.
"""

import operator
from typing import Annotated, TypedDict

from app.agent.schemas import (
    Conflict,
    Evidence,
    Report,
    ResearchPlan,
    Source,
    Topic,
    TopicResult,
)

TopicResults = Annotated[list[TopicResult], operator.add]


class ResearchInput(TypedDict):
    question: str


class ResearchState(ResearchInput, total=False):
    plan: ResearchPlan
    topic_results: TopicResults
    conflicts: list[Conflict]
    report: Report


# --- Research subgraph -------------------------------------------------------
# Each topic runs through its own subgraph with private working state. Only
# `topic_results` flows back to the parent; everything else stays local.


class TopicTask(TypedDict):
    """Input for one research branch (sent via `Send`)."""

    question: str
    topic: Topic


class TopicState(TopicTask, total=False):
    candidates: list[Source]  # everything search returned
    sources: list[Source]  # passed evaluation, best first
    rejected: list[Source]
    summary: str
    evidence: list[Evidence]
    error: str
    topic_results: TopicResults


class TopicOutput(TypedDict):
    topic_results: TopicResults
