import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { Assessment } from "@/lib/types";
import { cn } from "@/lib/utils";

const TYPE_LABEL: Record<Assessment["source_type"], string> = {
  academic: "Academic",
  government: "Government",
  news: "News",
  industry: "Industry",
  reference: "Reference",
  blog: "Blog",
  forum: "Forum",
  other: "Other",
};

export function sourceTypeLabel(type: Assessment["source_type"]) {
  return TYPE_LABEL[type];
}

/** Five ticks for a 1-5 credibility score. */
export function CredibilityMeter({ assessment, className }: { assessment: Assessment; className?: string }) {
  const level = assessment.credibility;
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          role="img"
          aria-label={`Credibility ${level} of 5`}
          className={cn("inline-flex items-end gap-[2px]", className)}
        >
          {[1, 2, 3, 4, 5].map((tick) => (
            <span
              key={tick}
              className={cn(
                "w-[3px] rounded-full",
                tick <= level
                  ? level >= 4
                    ? "bg-success"
                    : level === 3
                      ? "bg-warning"
                      : "bg-destructive/70"
                  : "bg-border",
              )}
              style={{ height: 4 + tick * 1.6 }}
            />
          ))}
        </span>
      </TooltipTrigger>
      <TooltipContent side="top" className="max-w-56 text-xs">
        Credibility {level}/5 · relevance {assessment.relevance}/5
        <br />
        <span className="opacity-80">{assessment.reason}</span>
      </TooltipContent>
    </Tooltip>
  );
}
