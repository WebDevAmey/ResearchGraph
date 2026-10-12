import { ArrowUpRight } from "lucide-react";

import { CredibilityMeter, sourceTypeLabel } from "@/components/research/credibility";
import { SourceFavicon } from "@/components/research/source-favicon";
import { paperByline, ProviderBadge, sourceOrigin } from "@/components/research/source-meta";
import type { SourceCard as SourceCardData } from "@/lib/types";
import { cn } from "@/lib/utils";

export function SourceCard({
  source,
  index,
  compact = false,
  highlighted = false,
}: {
  source: SourceCardData;
  index?: number;
  compact?: boolean;
  highlighted?: boolean;
}) {
  const { assessment } = source;
  const year = source.published_year ?? assessment?.published_year;
  const byline = paperByline(source);
  // For papers and Wikipedia the type would just repeat the provider badge.
  const showType = assessment && source.provider === "web";

  return (
    <article
      id={index ? `source-${index}` : undefined}
      className={cn(
        "group relative flex scroll-mt-24 flex-col gap-2 rounded-xl border bg-card p-3.5 transition-[border-color,box-shadow] hover:border-foreground/15",
        highlighted && "source-flash",
      )}
    >
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        {index !== undefined && <span className="font-mono tabular-nums text-cite">{index}</span>}
        <SourceFavicon domain={source.domain} />
        <span className="truncate">{sourceOrigin(source)}</span>
        <span className="relative z-10 ml-auto flex shrink-0 items-center gap-2">
          {year && !byline && <span className="tabular-nums">{year}</span>}
          {assessment && <CredibilityMeter assessment={assessment} />}
        </span>
      </div>
      <a
        href={source.url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-sm font-medium leading-snug text-balance after:absolute after:inset-0 hover:underline"
      >
        <span className={cn(compact ? "line-clamp-1" : "line-clamp-2")}>{source.title}</span>
      </a>
      {byline && <p className="text-xs text-muted-foreground tabular-nums">{byline}</p>}
      {!compact && source.snippet && (
        <p className="line-clamp-2 text-xs leading-relaxed text-muted-foreground">{source.snippet}</p>
      )}
      {!compact && (
        <span className="mt-auto flex flex-wrap gap-1.5">
          <ProviderBadge provider={source.provider} />
          {showType && (
            <span className="inline-flex items-center rounded-md bg-muted px-1.5 py-0.5 text-[10.5px] font-medium text-muted-foreground">
              {sourceTypeLabel(assessment.source_type)}
            </span>
          )}
        </span>
      )}
      <ArrowUpRight
        aria-hidden
        className="absolute right-3 bottom-3 size-3.5 text-muted-foreground/0 transition-colors group-hover:text-muted-foreground"
      />
    </article>
  );
}
