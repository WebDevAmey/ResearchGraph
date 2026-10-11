"use client";

// Adapted from VengeanceUI's Morph Text (github.com/Ashutoshx7/VengeanceUI).
// Changes: words stack in one grid cell so the width fits the longest word and
// the component can sit inline in a headline; it inherits the surrounding font
// instead of loading one; reduced motion shows the first word statically.

import { useId } from "react";

import { cn } from "@/lib/utils";

export interface MorphTextProps {
  words: string[];
  /** Milliseconds each word is shown. */
  interval?: number;
  className?: string;
}

export function MorphText({ words, interval = 2800, className }: MorphTextProps) {
  const filterId = `morph-${useId().replace(/:/g, "")}`;
  const total = (interval / 1000) * words.length;
  // Keyframe stops are percentages of the whole cycle; each word owns one slot.
  const slot = 100 / words.length;
  const at = (fraction: number) => `${(slot * fraction).toFixed(2)}%`;

  return (
    <span className={cn("morph-text inline-grid align-baseline", className)}>
      <svg aria-hidden focusable="false" className="pointer-events-none absolute size-0">
        <defs>
          <filter id={filterId}>
            <feColorMatrix
              in="SourceGraphic"
              type="matrix"
              values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 25 -9"
              result="goo"
            />
            <feComposite in="SourceGraphic" in2="goo" operator="atop" />
          </filter>
        </defs>
      </svg>
      <span className="sr-only">{words[0]}</span>
      <span aria-hidden className="inline-grid" style={{ filter: `url(#${filterId})` }}>
        {words.map((word, i) => (
          <span
            key={word}
            className="morph-word col-start-1 row-start-1 whitespace-nowrap"
            style={{
              animationName: "morph-word",
              animationDuration: `${total}s`,
              animationDelay: `${(i * interval) / 1000}s`,
            }}
          >
            {word}
          </span>
        ))}
      </span>
      <style>{`
        .morph-word {
          opacity: 0;
          animation-timing-function: ease-in-out;
          animation-iteration-count: infinite;
          animation-fill-mode: both;
        }
        @keyframes morph-word {
          0% { opacity: 0; filter: blur(14px); transform: scale(0.94); }
          ${at(0.06)} { opacity: 0.5; filter: blur(8px); }
          ${at(0.14)}, ${at(0.84)} { opacity: 1; filter: blur(0); transform: scale(1); }
          ${at(0.94)} { opacity: 0.4; filter: blur(8px); }
          ${at(1)}, 100% { opacity: 0; filter: blur(14px); transform: scale(1.04); }
        }
        @media (prefers-reduced-motion: reduce) {
          .morph-word { animation: none; }
          .morph-word:first-child { opacity: 1; }
        }
      `}</style>
    </span>
  );
}
