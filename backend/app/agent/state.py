"""Shared graph state.

Every node receives the current state and returns a *partial update*.
LangGraph merges updates into the state using each key's reducer:
- keys without a reducer are overwritten by the latest write;
- `topic_results` uses `operator.add`, so parallel research branches
  each append their result instead of clobbering each other.
"""

import operator
from typing import Annotated, TypedDict

from app.agent.schemas import Report, ResearchPlan, Topic, TopicResult


class ResearchInput(TypedDict):
    question: str


class ResearchState(ResearchInput, total=False):
    plan: ResearchPlan
    topic_results: Annotated[list[TopicResult], operator.add]
    report: Report


class TopicTask(TypedDict):
    """Private input for one parallel research branch (sent via `Send`)."""

    question: str
    topic: Topic
