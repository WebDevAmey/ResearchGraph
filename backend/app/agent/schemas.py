"""Data shapes that flow through the graph.

Two kinds of models live here:
- LLM output schemas (ResearchPlan, TopicAnalysis, ReportDraft): what Claude
  must return. Field descriptions are part of the prompt, so keep them precise.
- Domain models (Source, Finding, TopicResult, Report): what our code works
  with after validating and resolving the LLM output.
"""

from pydantic import BaseModel, Field

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


class KeyPoint(BaseModel):
    statement: str = Field(description="A single factual claim, stated precisely.")
    source_ids: list[int] = Field(
        description="Numbers of the sources that directly support this claim."
    )


class TopicAnalysis(BaseModel):
    summary: str = Field(description="2-4 sentence synthesis of what the sources say on this topic.")
    key_points: list[KeyPoint] = Field(description="The most important evidence-backed claims.")


class ReportDraft(BaseModel):
    title: str = Field(description="A concise, specific title for the report.")
    executive_summary: str = Field(description="One paragraph answering the question directly.")
    key_findings: list[str] = Field(description="3-7 headline findings, each one sentence.")
    detailed_analysis: str = Field(
        description="Markdown analysis organised with `###` subheadings, one per major theme."
    )
    limitations: str = Field(description="Gaps, weak evidence, or open questions in this research.")
    conclusion: str = Field(description="A short paragraph with the bottom-line answer.")


# --- Domain models ----------------------------------------------------------


class Source(BaseModel):
    url: str
    title: str
    content: str
    score: float = 0.0


class Finding(BaseModel):
    statement: str
    source_urls: list[str]


class TopicResult(BaseModel):
    topic: Topic
    summary: str = ""
    findings: list[Finding] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    error: str | None = None


class CitedSource(BaseModel):
    id: int
    url: str
    title: str


class Report(ReportDraft):
    sources: list[CitedSource]

    def to_markdown(self) -> str:
        findings = "\n".join(f"- {f}" for f in self.key_findings)
        sources = "\n".join(f"[{s.id}] {s.title} — {s.url}" for s in self.sources)
        return (
            f"# {self.title}\n\n"
            f"## Executive Summary\n\n{self.executive_summary}\n\n"
            f"## Key Findings\n\n{findings}\n\n"
            f"## Detailed Analysis\n\n{self.detailed_analysis}\n\n"
            f"## Limitations\n\n{self.limitations}\n\n"
            f"## Conclusion\n\n{self.conclusion}\n\n"
            f"## Sources\n\n{sources}\n"
        )
