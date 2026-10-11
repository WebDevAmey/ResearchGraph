import { ArrowUpRight } from "lucide-react";

import { CredibilityMeter, sourceTypeLabel } from "@/components/research/credibility";
import { SourceFavicon } from "@/components/research/source-favicon";
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
  return (
    <article
      id={index ? `source-${index}` : undefined}
      className={cn(
        "group relative flex scroll-mt-24 flex-col gap-2 rounded-xl border bg-card p-3.5 transition-[border-color,box-shadow] hover:border-foreground/15",
        highlighted && "source-flash",
      )}
    >
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        {index !== undefined && (
          <span className="font-mono tabular-nums text-cite">{index}</span>
        )}
        <SourceFavicon domain={source.domain} />
        <span className="truncate">{source.domain}</span>
        {assessment && (
          <span className="relative z-10 ml-auto flex shrink-0 items-center gap-2">
            {assessment.published_year && (
              <span className="tabular-nums">{assessment.published_year}</span>
            )}
            <CredibilityMeter assessment={assessment} />
          </span>
        )}
      </div>
      <a
        href={source.url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-sm font-medium leading-snug text-balance after:absolute after:inset-0 hover:underline"
      >
        <span className={cn(compact ? "line-clamp-1" : "line-clamp-2")}>{source.title}</span>
      </a>
      {!compact && source.snippet && (
        <p className="line-clamp-2 text-xs leading-relaxed text-muted-foreground">{source.snippet}</p>
      )}
      {assessment && !compact && (
        <span className="mt-auto inline-flex w-fit items-center rounded-md bg-muted px-1.5 py-0.5 text-[10.5px] font-medium text-muted-foreground">
          {sourceTypeLabel(assessment.source_type)}
        </span>
      )}
      <ArrowUpRight
        aria-hidden
        className="absolute right-3 bottom-3 size-3.5 text-muted-foreground/0 transition-colors group-hover:text-muted-foreground"
      />
    </article>
  );
}
