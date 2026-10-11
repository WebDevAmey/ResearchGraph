import type { Health, RunRecord } from "@/lib/types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(`Can't reach the research server at ${API_URL}.`, 0);
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = typeof body?.detail === "string" ? body.detail : response.statusText;
    throw new ApiError(detail || "Request failed.", response.status);
  }
  return (response.status === 204 ? undefined : await response.json()) as T;
}

export const api = {
  health: () => request<Health>("/api/health"),
  listRuns: (limit = 12) => request<RunRecord[]>(`/api/runs?limit=${limit}`),
  getRun: (id: string) => request<RunRecord>(`/api/runs/${encodeURIComponent(id)}`),
  createRun: (question: string) =>
    request<RunRecord>("/api/runs", { method: "POST", body: JSON.stringify({ question }) }),
  deleteRun: (id: string) =>
    request<void>(`/api/runs/${encodeURIComponent(id)}`, { method: "DELETE" }),
  eventsUrl: (id: string) => `${API_URL}/api/runs/${encodeURIComponent(id)}/events`,
};
