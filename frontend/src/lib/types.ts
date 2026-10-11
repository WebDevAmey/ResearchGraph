// Mirrors the backend's Pydantic models (backend/app/agent/schemas.py) and
// the progress events (backend/app/agent/events.py).

export type SourceType =
  | "academic"
  | "government"
  | "news"
  | "industry"
  | "reference"
  | "blog"
  | "forum"
  | "other";

export interface Assessment {
  relevance: number;
  credibility: number;
  source_type: SourceType;
  published_year: number | null;
  reason: string;
  quality: number;
}

export interface SourceCard {
  url: string;
  title: string;
  domain: string;
  snippet: string;
  assessment: Assessment | null;
}

export interface CitedSource extends SourceCard {
  id: number;
}

export interface ReportConflict {
  question: string;
  positions: { stance: string; source_ids: number[] }[];
  explanation: string;
  verdict: string;
}

export interface Report {
  title: string;
  executive_summary: string;
  key_findings: string[];
  detailed_analysis: string;
  conflicting_evidence: string;
  limitations: string;
  conclusion: string;
  sources: CitedSource[];
  conflicts: ReportConflict[];
}

export type RunStatus = "running" | "completed" | "failed";

export interface RunRecord {
  id: string;
  question: string;
  status: RunStatus;
  title: string | null;
  report: Report | null;
  error: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface Health {
  status: "ok";
  configured: boolean;
  demo: boolean;
}

export interface PlannedTopic {
  id: string;
  title: string;
  question: string;
  search_queries: string[];
}

export type RunEvent =
  | { type: "run_started"; question: string }
  | { type: "plan_ready"; understanding: string; topics: PlannedTopic[] }
  | { type: "topic_started"; topic_id: string }
  | { type: "sources_found"; topic_id: string; count: number }
  | { type: "sources_evaluated"; topic_id: string; kept: SourceCard[]; rejected: number }
  | {
      type: "topic_completed";
      topic_id: string;
      summary: string;
      evidence_count: number;
      error: string | null;
    }
  | { type: "conflicts_started" }
  | { type: "conflicts_ready"; count: number }
  | { type: "synthesis_started" }
  | { type: "report_ready"; report: Report }
  | { type: "run_failed"; error: string };

export const TERMINAL_EVENTS = new Set<RunEvent["type"]>(["report_ready", "run_failed"]);
