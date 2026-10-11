"use client";

// Adapted from Aceternity UI's Placeholders And Vanish Input (ui.aceternity.com).
// Changes: re-themed to our tokens, a labelled "Research" submit button, a
// single submit path (Enter no longer submits twice), `disabled` and
// `maxLength` support, and placeholder cycling that respects reduced motion.

import { ArrowRight } from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useCallback, useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

interface Particle {
  x: number;
  y: number;
  r: number;
  color: string;
}

export function PlaceholdersAndVanishInput({
  placeholders,
  onSubmit,
  disabled = false,
  maxLength = 500,
  submitLabel = "Research",
  ariaLabel,
}: {
  placeholders: string[];
  onSubmit: (value: string) => void;
  disabled?: boolean;
  maxLength?: number;
  submitLabel?: string;
  ariaLabel: string;
}) {
  const reduceMotion = useReducedMotion();
  const [placeholderIndex, setPlaceholderIndex] = useState(0);
  const [value, setValue] = useState("");
  const [animating, setAnimating] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const particlesRef = useRef<Particle[]>([]);

  useEffect(() => {
    if (reduceMotion || value) return;
    const id = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        setPlaceholderIndex((i) => (i + 1) % placeholders.length);
      }
    }, 3200);
    return () => window.clearInterval(id);
  }, [placeholders.length, reduceMotion, value]);

  const draw = useCallback(() => {
    const input = inputRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d", { willReadFrequently: true });
    if (!input || !canvas || !ctx) return;

    canvas.width = 800;
    canvas.height = 800;
    ctx.clearRect(0, 0, 800, 800);
    const styles = getComputedStyle(input);
    ctx.font = `${parseFloat(styles.fontSize) * 2}px ${styles.fontFamily}`;
    ctx.fillStyle = "#FFF";
    ctx.fillText(input.value, 16, 40);

    const pixels = ctx.getImageData(0, 0, 800, 800).data;
    const particles: Particle[] = [];
    for (let y = 0; y < 800; y++) {
      for (let x = 0; x < 800; x++) {
        const i = 4 * (y * 800 + x);
        if (pixels[i] && pixels[i + 1] && pixels[i + 2]) {
          particles.push({
            x,
            y,
            r: 1,
            color: `rgba(${pixels[i]}, ${pixels[i + 1]}, ${pixels[i + 2]}, ${pixels[i + 3]})`,
          });
        }
      }
    }
    particlesRef.current = particles;
  }, []);

  const animate = (start: number) => {
    const frame = (pos: number) => {
      requestAnimationFrame(() => {
        const next: Particle[] = [];
        for (const p of particlesRef.current) {
          if (p.x < pos) {
            next.push(p);
          } else if (p.r > 0) {
            p.x += Math.random() > 0.5 ? 1 : -1;
            p.y += Math.random() > 0.5 ? 1 : -1;
            p.r -= 0.05 * Math.random();
            next.push(p);
          }
        }
        particlesRef.current = next;
        const ctx = canvasRef.current?.getContext("2d");
        if (ctx) {
          ctx.clearRect(pos, 0, 800, 800);
          for (const { x, y, r, color } of next) {
            if (x > pos) {
              ctx.beginPath();
              ctx.rect(x, y, r, r);
              ctx.strokeStyle = color;
              ctx.stroke();
            }
          }
        }
        if (next.length > 0) {
          frame(pos - 8);
        } else {
          setValue("");
          setAnimating(false);
        }
      });
    };
    frame(start);
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const question = value.trim();
    if (!question || animating || disabled) return;
    onSubmit(question);
    if (reduceMotion) return;
    setAnimating(true);
    draw();
    animate(particlesRef.current.reduce((max, p) => Math.max(max, p.x), 0));
  };

  return (
    <form
      onSubmit={handleSubmit}
      className={cn(
        "relative mx-auto h-14 w-full overflow-hidden rounded-2xl border bg-card",
        "shadow-[0_1px_2px_rgba(0,0,0,0.04),0_8px_24px_-12px_rgba(0,0,0,0.12)]",
        "transition-[border-color,box-shadow] duration-200",
        "focus-within:border-ring/60 focus-within:shadow-[0_0_0_4px_var(--cite-soft),0_8px_24px_-12px_rgba(0,0,0,0.12)]",
      )}
    >
      <canvas
        ref={canvasRef}
        className={cn(
          "pointer-events-none absolute left-2 top-[22%] origin-top-left scale-50 pr-20 invert sm:left-4 dark:invert-0",
          animating ? "opacity-100" : "opacity-0",
        )}
      />
      <input
        ref={inputRef}
        value={value}
        onChange={(e) => !animating && setValue(e.target.value)}
        maxLength={maxLength}
        disabled={disabled}
        aria-label={ariaLabel}
        type="text"
        className={cn(
          "relative z-10 h-full w-full rounded-2xl border-none bg-transparent pl-4 pr-32 text-[15px] text-foreground sm:pl-5",
          "focus:outline-none disabled:cursor-not-allowed",
          animating && "text-transparent",
        )}
      />
      <button
        type="submit"
        disabled={!value.trim() || disabled}
        className={cn(
          "absolute right-2 top-1/2 z-20 flex h-10 -translate-y-1/2 items-center gap-1.5 rounded-xl px-4 text-sm font-medium",
          "bg-primary text-primary-foreground transition-[opacity,transform] active:scale-[0.97]",
          "disabled:cursor-not-allowed disabled:opacity-35",
        )}
      >
        {submitLabel}
        <ArrowRight className="size-4" aria-hidden />
      </button>
      <div className="pointer-events-none absolute inset-0 flex items-center rounded-2xl">
        <AnimatePresence mode="wait">
          {!value && (
            <motion.p
              key={placeholderIndex}
              initial={{ y: 5, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: -12, opacity: 0 }}
              transition={{ duration: 0.25, ease: "easeOut" }}
              className="w-[calc(100%-9rem)] truncate pl-4 text-left text-[15px] text-muted-foreground sm:pl-5"
            >
              {placeholders[placeholderIndex]}
            </motion.p>
          )}
        </AnimatePresence>
      </div>
    </form>
  );
}
