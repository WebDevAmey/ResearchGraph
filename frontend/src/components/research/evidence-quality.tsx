import { PROVIDERS } from "@/components/research/source-meta";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { Provider, ReportMetrics, RunUsage } from "@/lib/types";
import { cn } from "@/lib/utils";

const PROVIDER_COLOR: Record<Provider, string> = {
  web: "bg-foreground/70",
  academic: "bg-cite",
  reference: "bg-warning",
};

/** Signals computed in code from the run itself: what a reader should trust, and what it cost. */
export function EvidenceQuality({
  metrics,
  usage,
}: {
  metrics: ReportMetrics | null;
  usage: RunUsage | null;
}) {
  if (!metrics && !usage) return null;
  return (
    <section aria-labelledby="quality-heading" className="mt-10 border-t pt-6">
      <h2
        id="quality-heading"
        className="mb-3 font-mono text-[11px] uppercase tracking-[0.14em] text-muted-foreground"
      >
        Evidence quality
      </h2>
      {metrics && (
        <dl className="space-y-3 text-sm">
          <Row
            label="Verified quotes"
            hint="Share of evidence whose supporting quote was found word-for-word in its source."
            value={`${Math.round(metrics.verified_rate * 100)}%`}
            sub={`${metrics.verified_quotes} of ${metrics.evidence_items}`}
          >
            <Meter value={metrics.verified_rate} />
          </Row>
          <Row
            label="Sources cited"
            hint="Sources the report cites, out of every source the agent reviewed."
            value={String(metrics.sources_cited)}
            sub={`of ${metrics.sources_reviewed} reviewed`}
          />
          <Row
            label="Independent domains"
            hint="Distinct websites or publishers among cited sources."
            value={String(metrics.distinct_domains)}
          />
          {metrics.avg_credibility !== null && (
            <Row
              label="Avg. credibility"
              hint="Mean 1–5 credibility score of cited sources."
              value={metrics.avg_credibility.toFixed(1)}
              sub="/ 5"
            />
          )}
          <SourceMix providers={metrics.providers} />
        </dl>
      )}
      {usage && <UsageLine usage={usage} />}
    </section>
  );
}

function Row({
  label,
  hint,
  value,
  sub,
  children,
}: {
  label: string;
  hint: string;
  value: string;
  sub?: string;
  children?: React.ReactNode;
}) {
  return (
    <div>
      <div className="flex items-baseline justify-between gap-2">
        <Tooltip>
          <TooltipTrigger asChild>
            <dt className="cursor-help text-muted-foreground decoration-dotted underline-offset-4 hover:underline">
              {label}
            </dt>
          </TooltipTrigger>
          <TooltipContent side="right" className="max-w-56 text-xs">
            {hint}
          </TooltipContent>
        </Tooltip>
        <dd className="tabular-nums">
          <span className="font-medium">{value}</span>
          {sub && <span className="ml-1 text-xs text-muted-foreground">{sub}</span>}
        </dd>
      </div>
      {children}
    </div>
  );
}

function Meter({ value }: { value: number }) {
  return (
    <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-border" aria-hidden>
      <div
        className={cn(
          "h-full rounded-full",
          value >= 0.8 ? "bg-success" : value >= 0.5 ? "bg-warning" : "bg-destructive",
        )}
        style={{ width: `${Math.round(value * 100)}%` }}
      />
    </div>
  );
}

function SourceMix({ providers }: { providers: ReportMetrics["providers"] }) {
  const entries = (Object.keys(PROVIDERS) as Provider[])
    .map((p) => [p, providers[p] ?? 0] as const)
    .filter(([, n]) => n > 0);
  const total = entries.reduce((sum, [, n]) => sum + n, 0);
  if (!total) return null;
  return (
    <div>
      <dt className="text-muted-foreground">Source mix</dt>
      <dd>
        <div className="mt-1.5 flex h-1.5 gap-0.5 overflow-hidden rounded-full" aria-hidden>
          {entries.map(([p, n]) => (
            <div key={p} className={PROVIDER_COLOR[p]} style={{ width: `${(n / total) * 100}%` }} />
          ))}
        </div>
        <ul className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
          {entries.map(([p, n]) => (
            <li key={p} className="flex items-center gap-1.5">
              <span className={cn("size-1.5 rounded-full", PROVIDER_COLOR[p])} aria-hidden />
              {PROVIDERS[p].label} <span className="tabular-nums text-foreground">{n}</span>
            </li>
          ))}
        </ul>
      </dd>
    </div>
  );
}

function UsageLine({ usage }: { usage: RunUsage }) {
  if (!usage.calls) return null;
  const tokens = usage.input_tokens + usage.output_tokens;
  return (
    <p className="mt-5 text-xs leading-relaxed text-muted-foreground tabular-nums">
      {usage.calls} model calls · {formatTokens(tokens)} tokens
      {usage.cost_usd !== null && (
        <>
          {" · "}
          <span className="text-foreground">${usage.cost_usd.toFixed(2)}</span> est.
        </>
      )}
    </p>
  );
}

function formatTokens(n: number) {
  return n >= 1000 ? `${(n / 1000).toFixed(n >= 100_000 ? 0 : 1)}k` : String(n);
}
