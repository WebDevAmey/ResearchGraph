import { describe, expect, it } from "vitest";

import { deriveSteps, initialView, keptSources, reduceView } from "@/lib/research-state";
import type { Report, RunEvent, SourceCard } from "@/lib/types";

const card = (n: number): SourceCard => ({
  url: `https://example.com/${n}`,
  title: `Source ${n}`,
  domain: "example.com",
  snippet: "",
  provider: "web",
  published_year: null,
  authors: [],
  venue: null,
  citations: null,
  assessment: null,
});

const report = { title: "R", sources: [{ ...card(1), id: 1 }] } as Report;

const plan: Extract<RunEvent, { type: "plan_ready" }> = {
  type: "plan_ready",
  understanding: "u",
  time_sensitive: false,
  topics: [
    { id: "t1", title: "A", question: "qa", search_queries: ["a"] },
    { id: "t2", title: "B", question: "qb", search_queries: ["b"] },
  ],
};

const fold = (events: RunEvent[]) => events.reduce(reduceView, initialView);
const states = (events: RunEvent[]) =>
  Object.fromEntries(deriveSteps(fold(events)).map((s) => [s.key, s.state]));

describe("reduceView", () => {
  it("tracks a topic through its lifecycle", () => {
    const view = fold([
      { type: "run_started", question: "q" },
      plan,
      { type: "topic_started", topic_id: "t1" },
      { type: "sources_found", topic_id: "t1", count: 3 },
      { type: "sources_evaluated", topic_id: "t1", kept: [card(1), card(2)], rejected: 1 },
      { type: "topic_completed", topic_id: "t1", summary: "s", evidence_count: 2, error: null },
      { type: "topic_completed", topic_id: "t2", summary: "", evidence_count: 0, error: "No sources found." },
    ]);
    expect(view.status).toBe("running");
    expect(view.topics.map((t) => t.status)).toEqual(["done", "failed"]);
    expect(view.topics[0]).toMatchObject({ found: 3, rejected: 1, evidenceCount: 2 });
    expect(view.topics[1].error).toBe("No sources found.");
  });

  it("deduplicates kept sources across topics", () => {
    const view = fold([
      plan,
      { type: "sources_evaluated", topic_id: "t1", kept: [card(1), card(2)], rejected: 0 },
      { type: "sources_evaluated", topic_id: "t2", kept: [card(2), card(3)], rejected: 0 },
    ]);
    expect(keptSources(view).map((s) => s.title)).toEqual(["Source 1", "Source 2", "Source 3"]);
  });

  it("completes with a report and resets cleanly", () => {
    const done = fold([{ type: "run_started", question: "q" }, { type: "report_ready", report }]);
    expect(done).toMatchObject({ status: "completed", synthesis: "done", report });
    expect(reduceView(done, { type: "reset" })).toEqual(initialView);
  });
});

describe("deriveSteps", () => {
  it("starts with only the first step active", () => {
    expect(states([{ type: "run_started", question: "q" }])).toEqual({
      understand: "active",
      plan: "pending",
      research: "pending",
      evaluate: "pending",
      crosscheck: "pending",
      synthesize: "pending",
    });
  });

  it("moves through research to synthesis", () => {
    const researching = states([plan, { type: "sources_found", topic_id: "t1", count: 4 }]);
    expect(researching).toMatchObject({ plan: "done", research: "active", evaluate: "active" });

    const synthesising = states([
      plan,
      { type: "conflicts_started" },
      { type: "conflicts_ready", count: 1 },
      { type: "synthesis_started" },
    ]);
    expect(synthesising).toMatchObject({ research: "done", crosscheck: "done", synthesize: "active" });
  });

  it("marks cross-checking skipped when the server skipped it", () => {
    expect(states([plan, { type: "synthesis_started" }]).crosscheck).toBe("skipped");
  });

  it("marks the active step failed when the run fails", () => {
    const steps = states([plan, { type: "run_failed", error: "boom" }]);
    expect(steps.research).toBe("failed");
  });

  it("notes recency weighting for time-sensitive questions", () => {
    const step = deriveSteps(fold([{ ...plan, time_sensitive: true }])).find((s) => s.key === "plan");
    expect(step?.detail).toBe("2 topics · newer sources ranked higher");
  });

  it("labels the research step with the topic count", () => {
    const research = deriveSteps(fold([plan])).find((s) => s.key === "research");
    expect(research?.label).toBe("Researching 2 topics in parallel");
  });
});
