"use client";

import { AlertTriangle, ArrowLeft, Check, Copy, Download, RotateCcw, WifiOff } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { AgentThinking } from "@/components/agent-thinking";
import { LivePanel } from "@/components/research/live-panel";
import { REPORT_SECTIONS, ReportView } from "@/components/research/report-view";
import { RunTimeline } from "@/components/research/run-timeline";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Skeleton } from "@/components/ui/skeleton";
import { useResearchRun } from "@/hooks/use-research-run";
import { api, ApiError } from "@/lib/api";
import { duration, reportToMarkdown } from "@/lib/format";
import { activeStepLabel, type ResearchView as View } from "@/lib/research-state";
import type { RunRecord } from "@/lib/types";

type Loaded = { kind: "loading" } | { kind: "ready"; run: RunRecord } | { kind: "missing" } | { kind: "error"; message: string };

export function ResearchView({ id }: { id: string }) {
  const [loaded, setLoaded] = useState<Loaded>({ kind: "loading" });

  useEffect(() => {
    api
      .getRun(id)
      .then((run) => setLoaded({ kind: "ready", run }))
      .catch((error) =>
        setLoaded(
          error instanceof ApiError && error.status === 404
            ? { kind: "missing" }
            : { kind: "error", message: error instanceof Error ? error.message : "Something went wrong." },
        ),
      );
  }, [id]);

  if (loaded.kind === "loading") return <PageSkeleton />;
  if (loaded.kind === "missing") {
    return (
      <EmptyState
        title="Research not found"
        body="This run may have been deleted, or the link is incomplete."
      />
    );
  }
  if (loaded.kind === "error") {
    return <EmptyState title="Can’t load this research" body={loaded.message} icon={<WifiOff className="size-5" />} />;
  }
  return <RunPage key={loaded.run.id} run={loaded.run} />;
}

function RunPage({ run }: { run: RunRecord }) {
  const { view, connection } = useResearchRun(run.id);
  const question = view.question ?? run.question;
  const running = view.status === "running" || view.status === "connecting";
  const finishedAt = useCompletedAt(run, view.status);

  return (
    <div className="mx-auto w-full max-w-6xl px-4 pt-6 pb-24 sm:px-6">
      <Link
        href="/"
        className="inline-flex items-center gap-1.5 rounded-md text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="size-3.5" /> New research
      </Link>

      <header className="mt-6 mb-10 max-w-3xl">
        <h1 className="font-serif text-[clamp(1.9rem,4.4vw,2.9rem)] leading-[1.08] tracking-[-0.01em] text-balance">
          {view.report?.title ?? question}
        </h1>
        {view.report && <p className="mt-3 text-[15px] text-muted-foreground">{question}</p>}
        <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted-foreground">
          {running ? (
            <AgentThinking label={activeStepLabel(view)} />
          ) : view.status === "completed" ? (
            <span className="inline-flex items-center gap-1.5">
              <Check className="size-3.5 text-success" /> Completed
              {finishedAt && <span className="tabular-nums">in {duration(run.created_at, finishedAt)}</span>}
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 text-destructive">
              <AlertTriangle className="size-3.5" /> Failed
            </span>
          )}
          {view.report && <ReportActions question={question} view={view} />}
        </div>
        {connection !== "open" && running && (
          <p className="mt-3 inline-flex items-center gap-2 rounded-md bg-warning/10 px-2.5 py-1 text-xs text-foreground">
            <WifiOff className="size-3.5" />
            {connection === "reconnecting"
              ? "Connection interrupted, reconnecting…"
              : "Lost connection to the server. Refresh to try again."}
          </p>
        )}
      </header>

      <div className="grid gap-10 lg:grid-cols-[260px_minmax(0,1fr)] lg:gap-14">
        <aside className="lg:sticky lg:top-20 lg:self-start">
          <MobileCollapsible done={!running}>
            <RunTimeline view={view} />
            {view.report && <Contents />}
          </MobileCollapsible>
        </aside>

        <div className="min-w-0 max-w-3xl">
          {view.status === "failed" ? (
            <FailurePanel question={question} message={view.error} />
          ) : view.report ? (
            <ReportView report={view.report} />
          ) : (
            <LivePanel view={view} />
          )}
        </div>
      </div>
    </div>
  );
}

/** When the run finished: known up front for history, fetched once a live run ends. */
function useCompletedAt(run: RunRecord, status: View["status"]): string | null {
  const [fetched, setFetched] = useState<string | null>(null);
  const live = !run.completed_at && (status === "completed" || status === "failed");
  useEffect(() => {
    if (!live) return;
    api
      .getRun(run.id)
      .then((r) => setFetched(r.completed_at))
      .catch(() => undefined);
  }, [live, run.id]);
  return run.completed_at ?? fetched;
}

function MobileCollapsible({ done, children }: { done: boolean; children: React.ReactNode }) {
  // On small screens the activity log collapses once the report is ready.
  // Adjusting state during render (not in an effect) when `done` flips.
  const [open, setOpen] = useState(!done);
  const [wasDone, setWasDone] = useState(done);
  if (done !== wasDone) {
    setWasDone(done);
    setOpen(!done);
  }
  return (
    <>
      <div className="hidden lg:block">{children}</div>
      <Collapsible open={open} onOpenChange={setOpen} className="rounded-xl border bg-card lg:hidden">
        <CollapsibleTrigger className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium">
          Agent activity
          <span className="text-xs font-normal text-muted-foreground">{open ? "Hide" : "Show"}</span>
        </CollapsibleTrigger>
        <CollapsibleContent className="overflow-hidden px-4 pb-4 data-[state=closed]:animate-collapsible-up data-[state=open]:animate-collapsible-down">
          {children}
        </CollapsibleContent>
      </Collapsible>
    </>
  );
}

function Contents() {
  return (
    <nav aria-label="Report contents" className="mt-10 border-t pt-6">
      <p className="mb-2 font-mono text-[11px] uppercase tracking-[0.14em] text-muted-foreground">Contents</p>
      <ul className="space-y-0.5">
        {REPORT_SECTIONS.map((s) => (
          <li key={s.id}>
            <a
              href={`#${s.id}`}
              className="block rounded-md px-2 py-1 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            >
              {s.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

function ReportActions({ question, view }: { question: string; view: View }) {
  const [copied, setCopied] = useState(false);
  if (!view.report) return null;
  const markdown = reportToMarkdown(view.report, question);

  async function copy() {
    try {
      await navigator.clipboard.writeText(markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      toast.error("Couldn’t copy to the clipboard.");
    }
  }

  function download() {
    const url = URL.createObjectURL(new Blob([markdown], { type: "text/markdown" }));
    const link = Object.assign(document.createElement("a"), {
      href: url,
      download: `${view.report!.title.replace(/[^\w-]+/g, "-").toLowerCase().slice(0, 60)}.md`,
    });
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <span className="ml-auto flex gap-1">
      <Button variant="ghost" size="sm" onClick={copy} className="h-8 gap-1.5 text-muted-foreground">
        {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
        {copied ? "Copied" : "Copy"}
      </Button>
      <Button variant="ghost" size="sm" onClick={download} className="h-8 gap-1.5 text-muted-foreground">
        <Download className="size-3.5" /> Markdown
      </Button>
    </span>
  );
}

function FailurePanel({ question, message }: { question: string; message: string | null }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);

  async function retry() {
    setPending(true);
    try {
      const run = await api.createRun(question);
      router.push(`/research/${run.id}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not restart research.");
      setPending(false);
    }
  }

  return (
    <div role="alert" className="rounded-xl border border-destructive/25 bg-destructive/[0.04] p-6">
      <div className="flex items-center gap-2 font-medium">
        <AlertTriangle className="size-4 text-destructive" /> Research could not be completed
      </div>
      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
        {message ?? "Something went wrong while researching this question."}
      </p>
      <div className="mt-5 flex flex-wrap gap-2">
        <Button size="sm" onClick={retry} disabled={pending} className="gap-1.5">
          <RotateCcw className="size-3.5" /> Try again
        </Button>
        <Button size="sm" variant="outline" asChild>
          <Link href="/">Ask something else</Link>
        </Button>
      </div>
    </div>
  );
}

function EmptyState({ title, body, icon }: { title: string; body: string; icon?: React.ReactNode }) {
  return (
    <div className="mx-auto flex max-w-md flex-1 flex-col items-center justify-center px-6 py-24 text-center">
      {icon && <div className="mb-4 rounded-full border bg-card p-3 text-muted-foreground">{icon}</div>}
      <h1 className="font-serif text-3xl">{title}</h1>
      <p className="mt-2 text-sm text-muted-foreground">{body}</p>
      <Button asChild size="sm" className="mt-6">
        <Link href="/">Start new research</Link>
      </Button>
    </div>
  );
}

function PageSkeleton() {
  return (
    <div className="mx-auto w-full max-w-6xl px-4 pt-6 sm:px-6" aria-busy>
      <Skeleton className="h-4 w-28" />
      <Skeleton className="mt-8 h-10 w-3/4 max-w-2xl" />
      <Skeleton className="mt-3 h-4 w-40" />
      <div className="mt-12 grid gap-14 lg:grid-cols-[260px_minmax(0,1fr)]">
        <div className="space-y-5">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-5 w-4/5" />
          ))}
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-[104px] rounded-xl" />
          ))}
        </div>
      </div>
    </div>
  );
}
