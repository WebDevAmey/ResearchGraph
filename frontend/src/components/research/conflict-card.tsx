import { Scale } from "lucide-react";

import { CitedText } from "@/components/research/citation";
import type { ReportConflict } from "@/lib/types";

export function ConflictCard({ conflict }: { conflict: ReportConflict }) {
  return (
    <article className="overflow-hidden rounded-xl border bg-card">
      <h4 className="border-b px-4 py-3 font-serif text-lg leading-snug">{conflict.question}</h4>
      <div className="grid divide-y sm:grid-cols-2 sm:divide-x sm:divide-y-0">
        {conflict.positions.map((position, i) => (
          <div key={i} className="p-4">
            <p className="mb-1.5 font-mono text-[10.5px] uppercase tracking-[0.12em] text-muted-foreground">
              Position {String.fromCharCode(65 + i)}
            </p>
            <p className="text-sm leading-relaxed">
              <CitedText parts={[position.stance, " ", ...position.source_ids]} />
            </p>
          </div>
        ))}
      </div>
      <div className="space-y-2 border-t bg-muted/40 px-4 py-3 text-sm leading-relaxed">
        <p className="text-muted-foreground">
          <span className="font-medium text-foreground">Why they differ. </span>
          {conflict.explanation}
        </p>
        <p className="flex gap-2">
          <Scale className="mt-1 size-3.5 shrink-0 text-cite" aria-hidden />
          <span>
            <span className="font-medium">Weight of evidence. </span>
            {conflict.verdict}
          </span>
        </p>
      </div>
    </article>
  );
}
