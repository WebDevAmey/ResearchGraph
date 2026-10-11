"use client";

import { ArrowUpRight, Trash2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { ThinkingDots } from "@/components/agent-thinking";
import { BlurFade } from "@/components/ui/blur-fade";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { relativeTime } from "@/lib/format";
import type { RunRecord } from "@/lib/types";
import { cn } from "@/lib/utils";

export function RecentRuns() {
  const [runs, setRuns] = useState<RunRecord[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    api
      .listRuns()
      .then(setRuns)
      .catch(() => setFailed(true));
  }, []);

  async function remove(run: RunRecord) {
    setRuns((current) => current?.filter((r) => r.id !== run.id) ?? null);
    try {
      await api.deleteRun(run.id);
    } catch (error) {
      setRuns((current) => (current ? [run, ...current] : current));
      toast.error(error instanceof Error ? error.message : "Could not delete.");
    }
  }

  if (failed || (runs && runs.length === 0)) return null;

  return (
    <section aria-labelledby="recent-heading" className="w-full">
      <h2 id="recent-heading" className="mb-3 px-1 font-mono text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
        Recent research
      </h2>
      {runs === null ? (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-14 rounded-xl" />
          ))}
        </div>
      ) : (
        <ul className="divide-y overflow-hidden rounded-xl border bg-card">
          {runs.map((run, i) => (
            <li key={run.id} className="group relative transition-colors hover:bg-accent/60">
              <BlurFade
                delay={i * 0.04}
                offset={4}
                direction="up"
                className="flex items-center gap-3 px-4 py-3"
              >
                <StatusMark status={run.status} />
                <div className="min-w-0 flex-1">
                  <Link
                    href={`/research/${run.id}`}
                    className="block truncate text-sm font-medium after:absolute after:inset-0"
                  >
                    {run.title ?? run.question}
                  </Link>
                  {run.title && (
                    <p className="truncate text-xs text-muted-foreground">{run.question}</p>
                  )}
                </div>
                <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
                  {relativeTime(run.created_at)}
                </span>
                {run.status !== "running" && (
                  <button
                    type="button"
                    onClick={() => remove(run)}
                    aria-label={`Delete “${run.title ?? run.question}”`}
                    className="relative z-10 rounded-md p-1.5 text-muted-foreground opacity-0 transition-opacity hover:bg-background hover:text-destructive focus-visible:opacity-100 group-hover:opacity-100"
                  >
                    <Trash2 className="size-3.5" />
                  </button>
                )}
                <ArrowUpRight className="size-4 shrink-0 text-muted-foreground/50 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
              </BlurFade>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function StatusMark({ status }: { status: RunRecord["status"] }) {
  if (status === "running") return <ThinkingDots className="text-cite" />;
  return (
    <span
      aria-label={status}
      className={cn(
        "size-2 shrink-0 rounded-full",
        status === "completed" ? "bg-success" : "bg-destructive",
      )}
    />
  );
}
