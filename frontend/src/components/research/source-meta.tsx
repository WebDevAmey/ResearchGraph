import { BookOpen, Globe, GraduationCap, type LucideIcon } from "lucide-react";

import type { Provider, SourceCard } from "@/lib/types";
import { cn } from "@/lib/utils";

export const PROVIDERS: Record<Provider, { label: string; icon: LucideIcon }> = {
  web: { label: "Web", icon: Globe },
  academic: { label: "Paper", icon: GraduationCap },
  reference: { label: "Wikipedia", icon: BookOpen },
};

export function ProviderBadge({ provider, className }: { provider: Provider; className?: string }) {
  const { label, icon: Icon } = PROVIDERS[provider];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md bg-muted px-1.5 py-0.5 text-[10.5px] font-medium text-muted-foreground",
        provider === "academic" && "bg-cite-soft text-cite",
        className,
      )}
    >
      <Icon className="size-3" aria-hidden />
      {label}
    </span>
  );
}

/** Where a source was published: the journal for papers, the site for everything else. */
export function sourceOrigin(source: SourceCard): string {
  return source.provider === "academic" && source.venue ? source.venue : source.domain;
}

/** "Lovelace, Turing et al. · 2025 · cited by 12" for papers; null otherwise. */
export function paperByline(source: SourceCard): string | null {
  if (source.provider !== "academic") return null;
  const surnames = source.authors.slice(0, 2).map((a) => a.split(" ").at(-1));
  const parts = [
    surnames.length ? surnames.join(", ") + (source.authors.length > 2 ? " et al." : "") : null,
    source.published_year?.toString() ?? null,
    source.citations !== null ? `cited by ${source.citations.toLocaleString()}` : null,
  ];
  return parts.filter(Boolean).join(" · ") || null;
}
