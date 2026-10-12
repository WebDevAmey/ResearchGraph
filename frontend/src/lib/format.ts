import type { Report } from "@/lib/types";

export function relativeTime(iso: string, now = Date.now()): string {
  const seconds = Math.round((now - new Date(iso).getTime()) / 1000);
  if (seconds < 45) return "just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function duration(fromIso: string, toIso: string): string {
  const seconds = Math.max(0, Math.round((new Date(toIso).getTime() - new Date(fromIso).getTime()) / 1000));
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m ? `${m}m ${s.toString().padStart(2, "0")}s` : `${s}s`;
}

export function faviconUrl(domain: string): string {
  return `https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=64`;
}

export function reportToMarkdown(report: Report, question: string): string {
  const sources = report.sources
    .map((s) => {
      const origin = s.provider === "academic" && s.venue ? ` (${s.venue}${s.published_year ? `, ${s.published_year}` : ""})` : "";
      return `[${s.id}] ${s.title}${origin} — ${s.url}`;
    })
    .join("\n");
  return [
    `# ${report.title}`,
    `> ${question}`,
    `## Executive Summary\n\n${report.executive_summary}`,
    `## Key Findings\n\n${report.key_findings.map((f) => `- ${f}`).join("\n")}`,
    `## Detailed Analysis\n\n${report.detailed_analysis}`,
    `## Conflicting Evidence\n\n${report.conflicting_evidence}`,
    `## Limitations\n\n${report.limitations}`,
    `## Conclusion\n\n${report.conclusion}`,
    `## Sources\n\n${sources}`,
  ].join("\n\n");
}
