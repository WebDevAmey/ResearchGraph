// Adapted from Magic UI's Dot Pattern (magicui.design).
// The original renders one animated <circle> per dot (thousands on a desktop
// viewport) and re-measures on resize. This version tiles a single SVG
// <pattern>: one element, no JavaScript, server-renderable. The animated
// "glow" variant was dropped because nothing here uses it.

import { useId } from "react";

import { cn } from "@/lib/utils";

interface DotPatternProps extends React.SVGProps<SVGSVGElement> {
  width?: number;
  height?: number;
  x?: number;
  y?: number;
  cx?: number;
  cy?: number;
  cr?: number;
  className?: string;
}

export function DotPattern({
  width = 16,
  height = 16,
  x = 0,
  y = 0,
  cx = 1,
  cy = 1,
  cr = 1,
  className,
  ...props
}: DotPatternProps) {
  const id = useId();
  return (
    <svg
      aria-hidden="true"
      className={cn("pointer-events-none absolute inset-0 h-full w-full text-neutral-400/80", className)}
      {...props}
    >
      <defs>
        <pattern id={id} width={width} height={height} x={x} y={y} patternUnits="userSpaceOnUse">
          <circle cx={cx} cy={cy} r={cr} fill="currentColor" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill={`url(#${id})`} />
    </svg>
  );
}
