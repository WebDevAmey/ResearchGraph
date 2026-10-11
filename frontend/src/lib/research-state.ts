/**
 * Folds the run's event stream into view state.
 *
 * Live runs, page refreshes, and history all go through this one function:
 * the server replays every stored event, and the reducer rebuilds the view.
 */

import type { PlannedTopic, Report, RunEvent, SourceCard } from "@/lib/types";

export type TopicStatus = "queued" | "searching" | "evaluating" | "analyzing" | "done" | "failed";

export interface TopicView extends PlannedTopic {
  status: TopicStatus;
  found: number | null;
  kept: SourceCard[];
  rejected: number;
  summary: string;
  evidenceCount: number;
  error: string | null;
}

export type Phase = "idle" | "running" | "done";

export interface ResearchView {
  status: "connecting" | "running" | "completed" | "failed";
  question: string | null;
  understanding: string | null;
  topics: TopicView[];
  conflicts: { phase: Phase; count: number };
  synthesis: Phase;
  report: Report | null;
  error: string | null;
}

export const initialView: ResearchView = {
  status: "connecting",
  question: null,
  understanding: null,
  topics: [],
  conflicts: { phase: "idle", count: 0 },
  synthesis: "idle",
  report: null,
  error: null,
};

export type ViewAction = RunEvent | { type: "reset" };

export function reduceView(view: ResearchView, event: ViewAction): ResearchView {
  switch (event.type) {
    case "reset":
      return initialView;
    case "run_started":
      return { ...view, status: "running", question: event.question };
    case "plan_ready":
      return {
        ...view,
        understanding: event.understanding,
        topics: event.topics.map((t) => ({
          ...t,
          status: "queued",
          found: null,
          kept: [],
          rejected: 0,
          summary: "",
          evidenceCount: 0,
          error: null,
        })),
      };
    case "topic_started":
      return updateTopic(view, event.topic_id, { status: "searching" });
    case "sources_found":
      return updateTopic(view, event.topic_id, {
        found: event.count,
        status: event.count > 0 ? "evaluating" : "searching",
      });
    case "sources_evaluated":
      return updateTopic(view, event.topic_id, {
        kept: event.kept,
        rejected: event.rejected,
        status: "analyzing",
      });
    case "topic_completed":
      return updateTopic(view, event.topic_id, {
        summary: event.summary,
        evidenceCount: event.evidence_count,
        error: event.error,
        status: event.evidence_count > 0 ? "done" : "failed",
      });
    case "conflicts_started":
      return { ...view, conflicts: { phase: "running", count: 0 } };
    case "conflicts_ready":
      return { ...view, conflicts: { phase: "done", count: event.count } };
    case "synthesis_started":
      return { ...view, synthesis: "running" };
    case "report_ready":
      return { ...view, status: "completed", synthesis: "done", report: event.report };
    case "run_failed":
      return { ...view, status: "failed", error: event.error };
    default:
      return view;
  }
}

function updateTopic(view: ResearchView, id: string, patch: Partial<TopicView>): ResearchView {
  return { ...view, topics: view.topics.map((t) => (t.id === id ? { ...t, ...patch } : t)) };
}

// --- Derived data ------------------------------------------------------------

export type StepState = "pending" | "active" | "done" | "failed" | "skipped";

export interface Step {
  key: "understand" | "plan" | "research" | "evaluate" | "crosscheck" | "synthesize";
  label: string;
  state: StepState;
  detail: string | null;
}

const settled = (t: TopicView) => t.status === "done" || t.status === "failed";
const evaluated = (t: TopicView) => t.status === "analyzing" || settled(t);

export function deriveSteps(view: ResearchView): Step[] {
  const { topics } = view;
  const planned = topics.length > 0;
  const researchDone = planned && topics.every(settled);
  const evaluationDone = planned && topics.every(evaluated);
  const kept = topics.reduce((n, t) => n + t.kept.length, 0);
  const reviewed = topics.reduce((n, t) => n + t.kept.length + t.rejected, 0);
  const pastResearch = view.synthesis !== "idle" || view.conflicts.phase !== "idle";

  const steps: Step[] = [
    {
      key: "understand",
      label: "Understanding question",
      state: view.understanding ? "done" : "active",
      detail: view.understanding,
    },
    {
      key: "plan",
      label: "Creating research plan",
      state: planned ? "done" : view.understanding ? "active" : "pending",
      detail: planned ? `${topics.length} ${topics.length === 1 ? "topic" : "topics"}` : null,
    },
    {
      key: "research",
      label: planned
        ? `Researching ${topics.length} ${topics.length === 1 ? "topic" : "topics"} in parallel`
        : "Researching topics in parallel",
      state: researchDone || pastResearch ? "done" : planned ? "active" : "pending",
      detail: researchDone
        ? `${topics.filter((t) => t.status === "done").length} of ${topics.length} produced evidence`
        : null,
    },
    {
      key: "evaluate",
      label: "Evaluating sources",
      state: evaluationDone || pastResearch ? "done" : topics.some((t) => t.found) ? "active" : "pending",
      detail: reviewed ? `${kept} of ${reviewed} sources passed review` : null,
    },
    {
      key: "crosscheck",
      label: "Cross-checking evidence",
      state:
        view.conflicts.phase === "done"
          ? "done"
          : view.conflicts.phase === "running"
            ? "active"
            : view.synthesis !== "idle"
              ? "skipped"
              : "pending",
      detail:
        view.conflicts.phase === "done"
          ? view.conflicts.count
            ? `${view.conflicts.count} ${view.conflicts.count === 1 ? "conflict" : "conflicts"} found`
            : "No conflicts found"
          : null,
    },
    {
      key: "synthesize",
      label: "Synthesising findings",
      state: view.synthesis === "done" ? "done" : view.synthesis === "running" ? "active" : "pending",
      detail: view.report ? `${view.report.sources.length} sources cited` : null,
    },
  ];

  if (view.status === "failed") {
    const active = steps.find((s) => s.state === "active");
    if (active) active.state = "failed";
  }
  return steps;
}

/** Every source that passed review, across topics, de-duplicated by URL. */
export function keptSources(view: ResearchView): SourceCard[] {
  const byUrl = new Map<string, SourceCard>();
  for (const topic of view.topics) {
    for (const source of topic.kept) if (!byUrl.has(source.url)) byUrl.set(source.url, source);
  }
  return [...byUrl.values()];
}

export function activeStepLabel(view: ResearchView): string {
  if (view.status === "connecting") return "Connecting";
  const active = deriveSteps(view).find((s) => s.state === "active");
  return active?.label ?? "Working";
}
