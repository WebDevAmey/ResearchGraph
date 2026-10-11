"use client";

// Adapted from BoardUI's Agent Thinking (MIT, github.com/BoardUI/boardui):
// the dot-grid "wave" indicator, re-themed to our tokens and paired with the
// beUI shimmer label.

import { useEffect, useState } from "react";

import { TextShimmer } from "@/components/motion/text-shimmer";
import { cn } from "@/lib/utils";

const GRID = 3;
const SIZE = 3.5;
const GAP = 2;
const TICK_MS = 80;
const TRAIL = 0.3;
const MIN_OPACITY = 0.15;
const PHASE_STEP = 1 / 8;
// Static first frame: identical on server and client, and the resting state
// under prefers-reduced-motion.
const SEED = [0.55, 0.3, 0.15, 0.85, 0.55, 0.3, 1, 0.85, 0.55];

function opacities(phase: number) {
  const m = GRID - 1;
  return Array.from({ length: GRID * GRID }, (_, i) => {
    const s = (((i % GRID) + Math.floor(i / GRID)) / (2 * m)) * (GRID / (GRID + 1));
    const behind = (phase - s + 1) % 1;
    const lit = Math.max(0, 1 - behind / TRAIL) ** 1.5;
    return MIN_OPACITY + (1 - MIN_OPACITY) * lit;
  });
}

export function ThinkingDots({ className }: { className?: string }) {
  const [frame, setFrame] = useState(SEED);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let phase = 0;
    const id = window.setInterval(() => {
      phase = (phase + PHASE_STEP) % 1;
      setFrame(opacities(phase));
    }, TICK_MS);
    return () => window.clearInterval(id);
  }, []);

  return (
    <span
      aria-hidden
      className={cn("grid shrink-0", className)}
      style={{ gridTemplateColumns: `repeat(${GRID}, ${SIZE}px)`, gap: GAP }}
    >
      {frame.map((opacity, i) => (
        <span
          key={i}
          className="rounded-[1px] bg-current"
          style={{ width: SIZE, height: SIZE, opacity, transition: "opacity 220ms ease" }}
        />
      ))}
    </span>
  );
}

export function AgentThinking({ label, className }: { label: string; className?: string }) {
  return (
    <span role="status" className={cn("inline-flex items-center gap-2 text-sm", className)}>
      <ThinkingDots className="text-foreground/70" />
      <TextShimmer key={label} duration={2.2}>
        {label}
      </TextShimmer>
    </span>
  );
}
