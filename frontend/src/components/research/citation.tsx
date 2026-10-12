"use client";

import { ArrowUpRight } from "lucide-react";
import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";

import { CredibilityMeter } from "@/components/research/credibility";
import { paperByline, ProviderBadge, sourceOrigin } from "@/components/research/source-meta";
import { SourceFavicon } from "@/components/research/source-favicon";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import type { CitedSource } from "@/lib/types";
import { cn } from "@/lib/utils";

interface CitationContextValue {
  sources: Map<number, CitedSource>;
  highlighted: number | null;
  focusSource: (id: number) => void;
}

const CitationContext = createContext<CitationContextValue | null>(null);

export function CitationProvider({
  sources,
  children,
}: {
  sources: CitedSource[];
  children: React.ReactNode;
}) {
  const [highlighted, setHighlighted] = useState<number | null>(null);
  const timer = useRef<number | undefined>(undefined);
  const byId = useMemo(() => new Map(sources.map((s) => [s.id, s])), [sources]);

  const focusSource = useCallback((id: number) => {
    document.getElementById(`source-${id}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
    // Clear first so clicking the same citation twice replays the flash.
    setHighlighted(null);
    window.clearTimeout(timer.current);
    requestAnimationFrame(() => setHighlighted(id));
    timer.current = window.setTimeout(() => setHighlighted(null), 1700);
  }, []);

  return (
    <CitationContext.Provider value={{ sources: byId, highlighted, focusSource }}>
      {children}
    </CitationContext.Provider>
  );
}

export function useCitations() {
  const context = useContext(CitationContext);
  if (!context) throw new Error("useCitations must be used inside <CitationProvider>");
  return context;
}

export function Citation({ id }: { id: number }) {
  const { sources, focusSource } = useCitations();
  const source = sources.get(id);
  if (!source) return null;

  return (
    <HoverCard openDelay={120} closeDelay={80}>
      <HoverCardTrigger asChild>
        <button
          type="button"
          data-citation
          onClick={() => focusSource(id)}
          aria-label={`Source ${id}: ${source.title}`}
          className={cn(
            "mx-[1px] inline-flex h-[1.15rem] min-w-[1.15rem] -translate-y-[0.1em] items-center justify-center rounded-[5px] px-1",
            "bg-cite-soft align-baseline font-mono text-[10.5px] font-medium leading-none text-cite tabular-nums",
            "transition-colors hover:bg-cite hover:text-background focus-visible:outline-2 focus-visible:outline-cite",
          )}
        >
          {id}
        </button>
      </HoverCardTrigger>
      <HoverCardContent side="top" align="center" className="w-80 p-0">
        <div className="space-y-2 p-3.5">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <SourceFavicon domain={source.domain} />
            <span className="truncate">{sourceOrigin(source)}</span>
            <span className="ml-auto flex shrink-0 items-center gap-2">
              <ProviderBadge provider={source.provider} />
              {source.assessment && <CredibilityMeter assessment={source.assessment} />}
            </span>
          </div>
          <p className="text-sm font-medium leading-snug">{source.title}</p>
          {paperByline(source) && (
            <p className="text-xs text-muted-foreground tabular-nums">{paperByline(source)}</p>
          )}
          {source.snippet && (
            <p className="line-clamp-3 text-xs leading-relaxed text-muted-foreground">
              {source.snippet}
            </p>
          )}
        </div>
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-between border-t px-3.5 py-2 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          Open source
          <ArrowUpRight className="size-3.5" />
        </a>
      </HoverCardContent>
    </HoverCard>
  );
}

/** Plain text with [n] markers rendered as citations. */
export function CitedText({ parts }: { parts: (string | number)[] }) {
  return (
    <>
      {parts.map((part, i) =>
        typeof part === "number" ? <Citation key={i} id={part} /> : <span key={i}>{part}</span>,
      )}
    </>
  );
}
