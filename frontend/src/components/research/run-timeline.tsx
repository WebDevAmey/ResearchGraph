"use client";

import { Check, ChevronRight, Minus, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";

import { ThinkingDots } from "@/components/agent-thinking";
import { SourceFavicon } from "@/components/research/source-favicon";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { deriveSteps, type ResearchView, type Step, type TopicView } from "@/lib/research-state";
import { cn } from "@/lib/utils";

export function RunTimeline({ view }: { view: ResearchView }) {
  const steps = deriveSteps(view);
  return (
    <ol aria-label="Agent progress" className="relative">
      {steps.map((step, i) => (
        <li key={step.key} className="relative pb-5 pl-8 last:pb-0">
          {i < steps.length - 1 && (
            <span
              aria-hidden
              className={cn(
                "absolute top-6 bottom-0 left-[9px] w-px transition-colors duration-500",
                step.state === "done" ? "bg-foreground/25" : "bg-border",
              )}
            />
          )}
          <StepIcon state={step.state} />
          <div className="min-h-5">
            <p
              className={cn(
                "text-sm leading-5 transition-colors",
                step.state === "pending" || step.state === "skipped"
                  ? "text-muted-foreground"
                  : "text-foreground",
                step.state === "active" && "font-medium",
              )}
            >
              {step.label}
            </p>
            <StepDetail step={step} />
          </div>
          {step.key === "research" && view.topics.length > 0 && (
            <ul className="mt-3 space-y-1">
              {view.topics.map((topic) => (
                <TopicRow key={topic.id} topic={topic} />
              ))}
            </ul>
          )}
        </li>
      ))}
    </ol>
  );
}

function StepIcon({ state }: { state: Step["state"] }) {
  return (
    <span className="absolute top-0 left-0 flex size-5 items-center justify-center">
      <AnimatePresence mode="wait" initial={false}>
        <motion.span
          key={state}
          initial={{ scale: 0.6, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.6, opacity: 0 }}
          transition={{ duration: 0.18 }}
          className={cn(
            "flex size-5 items-center justify-center rounded-full",
            state === "done" && "bg-foreground text-background",
            state === "active" && "bg-cite-soft text-cite ring-1 ring-cite/30",
            state === "pending" && "ring-1 ring-border ring-inset",
            state === "failed" && "bg-destructive text-white",
            state === "skipped" && "ring-1 ring-border ring-inset text-muted-foreground",
          )}
        >
          {state === "done" && <Check className="size-3" strokeWidth={3} />}
          {state === "active" && <ThinkingDots className="scale-[0.7]" />}
          {state === "failed" && <X className="size-3" strokeWidth={3} />}
          {state === "skipped" && <Minus className="size-3" />}
        </motion.span>
      </AnimatePresence>
    </span>
  );
}

function StepDetail({ step }: { step: Step }) {
  if (!step.detail) return null;
  return (
    <motion.p
      initial={{ opacity: 0, y: -2 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "mt-0.5 text-xs leading-relaxed text-muted-foreground",
        step.key === "understand" && "line-clamp-3",
      )}
    >
      {step.detail}
    </motion.p>
  );
}

const TOPIC_STATUS: Record<TopicView["status"], string> = {
  queued: "Queued",
  searching: "Searching",
  evaluating: "Evaluating sources",
  analyzing: "Extracting evidence",
  done: "Done",
  failed: "No usable evidence",
};

function TopicRow({ topic }: { topic: TopicView }) {
  const [open, setOpen] = useState(false);
  const working = topic.status !== "done" && topic.status !== "failed";

  return (
    <li>
      <Collapsible open={open} onOpenChange={setOpen}>
        <CollapsibleTrigger className="group flex w-full items-start gap-2 rounded-lg px-2 py-1.5 text-left transition-colors hover:bg-accent">
          <ChevronRight
            aria-hidden
            className="mt-0.5 size-3.5 shrink-0 text-muted-foreground transition-transform duration-200 group-data-[state=open]:rotate-90"
          />
          <span className="min-w-0 flex-1">
            <span className="block truncate text-[13px] leading-5">{topic.title}</span>
            <span
              className={cn(
                "flex min-w-0 items-center gap-1.5 text-[11px] leading-4",
                topic.status === "failed" ? "text-destructive/80" : "text-muted-foreground",
              )}
            >
              {working && topic.status !== "queued" && (
                <ThinkingDots className="shrink-0 scale-[0.6] text-cite" />
              )}
              <span className="truncate tabular-nums">
                {TOPIC_STATUS[topic.status]}
                {topic.found !== null &&
                  topic.status !== "searching" &&
                  ` · ${topic.kept.length}/${topic.kept.length + topic.rejected || topic.found} sources`}
              </span>
            </span>
          </span>
          {topic.kept.length > 0 && (
            <span className="mt-1 flex shrink-0 -space-x-1">
              {topic.kept.slice(0, 3).map((s) => (
                <SourceFavicon key={s.url} domain={s.domain} className="size-3.5 ring-2 ring-background" />
              ))}
            </span>
          )}
        </CollapsibleTrigger>
        <CollapsibleContent className="overflow-hidden data-[state=closed]:animate-collapsible-up data-[state=open]:animate-collapsible-down">
          <div className="space-y-2 pt-1 pr-2 pb-2 pl-7 text-xs leading-relaxed text-muted-foreground">
            <p className="text-foreground/80">{topic.question}</p>
            <ul className="space-y-0.5 font-mono text-[11px]">
              {topic.search_queries.map((q) => (
                <li key={q} className="truncate">
                  ⌕ {q}
                </li>
              ))}
            </ul>
            {topic.summary && <p>{topic.summary}</p>}
            {topic.error && topic.status === "failed" && <p className="text-destructive/80">{topic.error}</p>}
          </div>
        </CollapsibleContent>
      </Collapsible>
    </li>
  );
}
