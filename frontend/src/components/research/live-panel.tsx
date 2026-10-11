"use client";

import { AgentThinking } from "@/components/agent-thinking";
import { SourceCard } from "@/components/research/source-card";
import { BlurFade } from "@/components/ui/blur-fade";
import { NumberTicker } from "@/components/ui/number-ticker";
import { Skeleton } from "@/components/ui/skeleton";
import { activeStepLabel, keptSources, type ResearchView } from "@/lib/research-state";

/** What the main column shows while the agent works: sources streaming in, then a draft skeleton. */
export function LivePanel({ view }: { view: ResearchView }) {
  const sources = keptSources(view);
  const reviewed = view.topics.reduce((n, t) => n + t.kept.length + t.rejected, 0);

  return (
    <div className="space-y-10">
      <section aria-live="polite">
        <div className="mb-4 flex items-baseline justify-between gap-4">
          <h2 className="font-serif text-[1.75rem] leading-tight">Sources</h2>
          {reviewed > 0 && (
            <p className="text-xs text-muted-foreground tabular-nums">
              <NumberTicker value={sources.length} className="text-foreground" /> of{" "}
              <NumberTicker value={reviewed} /> passed review
            </p>
          )}
        </div>
        {sources.length === 0 ? (
          <div className="grid gap-3 sm:grid-cols-2">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-[104px] rounded-xl" style={{ opacity: 1 - i * 0.18 }} />
            ))}
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {sources.map((source) => (
              <BlurFade key={source.url} offset={6} direction="up">
                <SourceCard source={source} />
              </BlurFade>
            ))}
          </div>
        )}
      </section>

      <section aria-label="Report draft" className="rounded-xl border border-dashed p-6">
        <AgentThinking
          label={view.synthesis === "running" ? "Writing the report" : `${activeStepLabel(view)}…`}
          className="text-muted-foreground"
        />
        <div className="mt-6 space-y-3">
          <Skeleton className="h-6 w-2/5" />
          <Skeleton className="h-3.5 w-full" />
          <Skeleton className="h-3.5 w-[92%]" />
          <Skeleton className="h-3.5 w-[78%]" />
          <Skeleton className="mt-6 h-6 w-1/3" />
          <Skeleton className="h-3.5 w-[88%]" />
          <Skeleton className="h-3.5 w-[64%]" />
        </div>
      </section>
    </div>
  );
}
