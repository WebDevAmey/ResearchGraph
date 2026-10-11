"use client";

import { useState } from "react";

import { faviconUrl } from "@/lib/format";
import { cn } from "@/lib/utils";

export function SourceFavicon({ domain, className }: { domain: string; className?: string }) {
  const [failed, setFailed] = useState(false);
  const base = cn(
    "inline-flex size-4 shrink-0 items-center justify-center overflow-hidden rounded-[4px] bg-muted ring-1 ring-border",
    className,
  );
  if (failed) {
    return (
      <span aria-hidden className={cn(base, "text-[9px] font-semibold uppercase text-muted-foreground")}>
        {domain.charAt(0)}
      </span>
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element -- tiny third-party favicons; next/image adds nothing here
    <img
      src={faviconUrl(domain)}
      alt=""
      width={16}
      height={16}
      loading="lazy"
      onError={() => setFailed(true)}
      className={base}
    />
  );
}
