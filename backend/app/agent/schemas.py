"""Data shapes that flow through the graph.

Two kinds of models live here:
- LLM output schemas: what Claude must return. Field descriptions are part
  of the prompt, so keep them precise.
- Domain models: what our code works with after validating and resolving
  the LLM output.
"""

from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, computed_field

SourceType = Literal[
    "academic", "government", "news", "industry", "reference", "blog", "forum", "other"
]

# --- LLM output schemas -----------------------------------------------------


class Topic(BaseModel):
    title: str = Field(description="Short label for the topic, 2-6 words.")
    question: str = Field(description="The specific sub-question this topic answers.")
    search_queries: list[str] = Field(
        description="1-3 distinct web search queries that would surface evidence for this topic."
    )


class ResearchPlan(BaseModel):
    understanding: str = Field(
        description="One or two sentences restating what the user wants to learn and why it matters."
    )
    topics: list[Topic] = Field(
        description="Independent research topics that together cover the question."
    )


class SourceAssessment(BaseModel):
    source_id: int = Field(description="The number of the source being assessed.")
    relevance: int = Field(description="1-5: how directly the source addresses the topic.")
    credibility: int = Field(description="1-5: how trustworthy the source is, per the rubric.")
    source_type: SourceType
    published_year: int | None = Field(
        description="Year of publication if stated in the URL or content, otherwise null."
    )
    reason: str = Field(description="Under 15 words justifying the scores.")


class SourceEvaluation(BaseModel):
    assessments: list[SourceAssessment] = Field(description="One assessment per source.")


class KeyPoint(BaseModel):
    statement: str = Field(description="A single factual claim, stated precisely.")
    quote: str = Field(
        description="A short verbatim excerpt (under 40 words) from the first cited source "
        "that supports the claim. Copy it exactly; do not paraphrase."
    )
    source_ids: list[int] = Field(
        description="Numbers of the sources that directly support this claim."
    )


class TopicAnalysis(BaseModel):
    summary: str = Field(description="2-4 sentence synthesis of what the sources say on this topic.")
    key_points: list[KeyPoint] = Field(description="The most important evidence-backed claims.")


class ConflictSide(BaseModel):
    stance: str = Field(description="The position this side takes, in one sentence.")
    evidence_ids: list[int] = Field(description="Numbers of the evidence items for this side.")


class ConflictFinding(BaseModel):
    question: str = Field(description="The specific point in dispute, phrased as a question.")
    sides: list[ConflictSide] = Field(description="The competing positions, at least two.")
    explanation: str = Field(
        description="Why the evidence diverges: methodology, timeframe, population, "
        "definitions, or incentives. Say so if the reason is unclear."
    )
    verdict: str = Field(
        description="Which side the weight of evidence favours and why, or that it is unresolved."
    )


class ConflictAnalysis(BaseModel):
    conflicts: list[ConflictFinding] = Field(
        description="Genuine disagreements only. Empty if the evidence is consistent."
    )


class ReportDraft(BaseModel):
    title: str = Field(description="A concise, specific title for the report.")
    executive_summary: str = Field(description="One paragraph answering the question directly.")
    key_findings: list[str] = Field(description="3-7 headline findings, each one sentence.")
    detailed_analysis: str = Field(
        description="Markdown analysis organised with `###` subheadings, one per major theme."
    )
    conflicting_evidence: str = Field(
        description="Markdown on where sources disagree, why, and which view is better "
        "supported. If there are no conflicts, say so in one sentence."
    )
    limitations: str = Field(description="Gaps, weak evidence, or open questions in this research.")
    conclusion: str = Field(description="A short paragraph with the bottom-line answer.")


# --- Domain models ----------------------------------------------------------


class Assessment(BaseModel):
    relevance: int
    credibility: int
    source_type: SourceType
    published_year: int | None = None
    reason: str
    quality: float  # 0-1, combines relevance and credibility

    @property
    def label(self) -> str:
        parts = [self.source_type, f"credibility {self.credibility}/5"]
        if self.published_year:
            parts.append(str(self.published_year))
        return " · ".join(parts)


class Source(BaseModel):
    url: str
    title: str
    content: str
    score: float = 0.0  # the search engine's own relevance score
    assessment: Assessment | None = None

    @computed_field
    @property
    def domain(self) -> str:
        return urlparse(self.url).netloc.removeprefix("www.")


class Evidence(BaseModel):
    statement: str
    quote: str
    quote_verified: bool  # the quote was found verbatim in a cited source
    source_urls: list[str]


class TopicResult(BaseModel):
    topic_id: str
    topic: Topic
    summary: str = ""
    evidence: list[Evidence] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    rejected_sources: list[Source] = Field(default_factory=list)
    error: str | None = None


class Position(BaseModel):
    stance: str
    source_urls: list[str]


class Conflict(BaseModel):
    question: str
    positions: list[Position]
    explanation: str
    verdict: str


class CitedSource(BaseModel):
    id: int
    url: str
    title: str
    domain: str
    snippet: str = ""
    assessment: Assessment | None = None


class CitedPosition(BaseModel):
    stance: str
    source_ids: list[int]


class ReportConflict(BaseModel):
    question: str
    positions: list[CitedPosition]
    explanation: str
    verdict: str


class Report(ReportDraft):
    sources: list[CitedSource]
    conflicts: list[ReportConflict] = Field(default_factory=list)

    def to_markdown(self) -> str:
        findings = "\n".join(f"- {f}" for f in self.key_findings)
        sources = "\n".join(
            f"[{s.id}] {s.title} — {s.url}" + (f" ({s.assessment.label})" if s.assessment else "")
            for s in self.sources
        )
        return (
            f"# {self.title}\n\n"
            f"## Executive Summary\n\n{self.executive_summary}\n\n"
            f"## Key Findings\n\n{findings}\n\n"
            f"## Detailed Analysis\n\n{self.detailed_analysis}\n\n"
            f"## Conflicting Evidence\n\n{self.conflicting_evidence}\n\n"
            f"## Limitations\n\n{self.limitations}\n\n"
            f"## Conclusion\n\n{self.conclusion}\n\n"
            f"## Sources\n\n{sources}\n"
        )
