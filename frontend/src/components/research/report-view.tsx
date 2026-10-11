"use client";

import { CitationProvider, CitedText, useCitations } from "@/components/research/citation";
import { ConflictCard } from "@/components/research/conflict-card";
import { Markdown } from "@/components/research/markdown";
import { SourceCard } from "@/components/research/source-card";
import { BlurFade } from "@/components/ui/blur-fade";
import { splitCitations } from "@/lib/citations";
import type { Report } from "@/lib/types";

export const REPORT_SECTIONS = [
  { id: "summary", label: "Executive Summary" },
  { id: "findings", label: "Key Findings" },
  { id: "analysis", label: "Detailed Analysis" },
  { id: "conflicts", label: "Conflicting Evidence" },
  { id: "limitations", label: "Limitations" },
  { id: "conclusion", label: "Conclusion" },
  { id: "sources", label: "Sources" },
] as const;

export function ReportView({ report }: { report: Report }) {
  return (
    <CitationProvider sources={report.sources}>
      <article className="space-y-12">
        <Section id="summary" label="Executive Summary" index={0}>
          <Markdown className="text-[17px] leading-[1.7] text-foreground">
            {report.executive_summary}
          </Markdown>
        </Section>

        <Section id="findings" label="Key Findings" index={1}>
          <ol className="space-y-3">
            {report.key_findings.map((finding, i) => (
              <li key={i} className="flex gap-4 text-[15.5px] leading-relaxed">
                <span className="mt-[3px] font-mono text-xs tabular-nums text-muted-foreground">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span>
                  <CitedText parts={splitCitations(finding)} />
                </span>
              </li>
            ))}
          </ol>
        </Section>

        <Section id="analysis" label="Detailed Analysis" index={2}>
          <Markdown>{report.detailed_analysis}</Markdown>
        </Section>

        <Section id="conflicts" label="Conflicting Evidence" index={3}>
          <Markdown>{report.conflicting_evidence}</Markdown>
          {report.conflicts.length > 0 && (
            <div className="mt-6 space-y-4">
              {report.conflicts.map((conflict, i) => (
                <ConflictCard key={i} conflict={conflict} />
              ))}
            </div>
          )}
        </Section>

        <Section id="limitations" label="Limitations" index={4}>
          <Markdown>{report.limitations}</Markdown>
        </Section>

        <Section id="conclusion" label="Conclusion" index={5}>
          <div className="border-l-2 border-cite pl-5">
            <Markdown>{report.conclusion}</Markdown>
          </div>
        </Section>

        <Section id="sources" label="Sources" index={6}>
          <SourceList report={report} />
        </Section>
      </article>
    </CitationProvider>
  );
}

function Section({
  id,
  label,
  index,
  children,
}: {
  id: string;
  label: string;
  index: number;
  children: React.ReactNode;
}) {
  return (
    // Staggered entrance when the report arrives, not on scroll: jumping from a
    // citation to its source should never land on half-faded content.
    <BlurFade delay={Math.min(index * 0.05, 0.25)}>
      <section id={id} aria-labelledby={`${id}-heading`} className="scroll-mt-24">
        <h2 id={`${id}-heading`} className="mb-4 font-serif text-[1.75rem] leading-tight tracking-[-0.005em]">
          {label}
        </h2>
        {children}
      </section>
    </BlurFade>
  );
}

function SourceList({ report }: { report: Report }) {
  const { highlighted } = useCitations();
  if (report.sources.length === 0) {
    return <p className="text-sm text-muted-foreground">No sources were cited.</p>;
  }
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {report.sources.map((source) => (
        <SourceCard key={source.id} source={source} index={source.id} highlighted={highlighted === source.id} />
      ))}
    </div>
  );
}
