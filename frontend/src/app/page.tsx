import { QuestionForm } from "@/components/home/question-form";
import { RecentRuns } from "@/components/home/recent-runs";
import { ServerStatus } from "@/components/home/server-status";
import { BlurFade } from "@/components/ui/blur-fade";
import { DotPattern } from "@/components/ui/dot-pattern";
import { MorphText } from "@/components/ui/morph-text";
import { cn } from "@/lib/utils";

const STEPS = [
  ["Plan", "Splits your question into independent topics"],
  ["Search", "Researches every topic in parallel"],
  ["Evaluate", "Scores each source for relevance and credibility"],
  ["Verify", "Checks quotes and cross-examines conflicting claims"],
  ["Synthesise", "Writes a report where every claim is cited"],
];

export default function Home() {
  return (
    <div className="relative flex flex-1 flex-col">
      <DotPattern
        width={22}
        height={22}
        cr={0.9}
        className={cn(
          "pointer-events-none -z-10 text-foreground/[0.09]",
          "[mask-image:radial-gradient(560px_circle_at_50%_30%,white,transparent)]",
        )}
      />

      <section className="mx-auto flex w-full max-w-2xl flex-col items-center px-4 pt-[12vh] pb-16 text-center sm:px-6">
        <BlurFade delay={0.05}>
          <p className="mb-5 font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
            Autonomous research agent
          </p>
        </BlurFade>
        <BlurFade delay={0.12}>
          <h1 className="font-serif text-[clamp(2.4rem,6.5vw,4.1rem)] leading-[1.04] tracking-[-0.01em] text-balance">
            Turn a question into{" "}
            <MorphText
              words={["evidence-backed", "cross-checked", "fully cited"]}
              className="italic text-cite"
            />{" "}
            research.
          </h1>
        </BlurFade>
        <BlurFade delay={0.2}>
          <p className="mx-auto mt-5 max-w-md text-[15px] leading-relaxed text-muted-foreground text-pretty">
            ResearchGraph plans an investigation, searches the web in parallel, weighs every source,
            and writes a report you can trace claim by claim.
          </p>
        </BlurFade>

        <BlurFade delay={0.28} className="mt-10 w-full">
          <QuestionForm />
        </BlurFade>
        <BlurFade delay={0.34} className="mt-6 w-full">
          <ServerStatus />
        </BlurFade>
      </section>

      <section className="mx-auto w-full max-w-2xl px-4 pb-20 sm:px-6">
        <RecentRuns />
      </section>

      <section aria-label="How it works" className="mt-auto border-t bg-card/40">
        <ol className="mx-auto grid max-w-6xl grid-cols-2 gap-x-6 gap-y-6 px-4 py-10 sm:px-6 md:grid-cols-5">
          {STEPS.map(([title, body], i) => (
            <li key={title} className="text-left">
              <p className="font-mono text-[11px] tabular-nums text-muted-foreground">0{i + 1}</p>
              <p className="mt-1 text-sm font-medium">{title}</p>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{body}</p>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
