import Link from "next/link";

import { ThemeToggle } from "@/components/motion/theme-toggle";

export function Logo({ className }: { className?: string }) {
  // Three nodes joined by edges: a question branching into evidence.
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden className={className}>
      <path d="M6 7.5 12 17M18 7.5 12 17M6 6h12" stroke="currentColor" strokeWidth="1.5" opacity="0.45" />
      <circle cx="6" cy="6" r="2.6" fill="currentColor" />
      <circle cx="18" cy="6" r="2.6" fill="currentColor" />
      <circle cx="12" cy="17.5" r="2.6" fill="var(--cite)" />
    </svg>
  );
}

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-transparent bg-background/80 backdrop-blur-md supports-[backdrop-filter]:bg-background/70">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link
          href="/"
          className="group flex items-center gap-2 rounded-md text-[15px] font-medium tracking-tight focus-visible:outline-2"
        >
          <Logo className="size-5 transition-transform duration-300 group-hover:rotate-[-8deg]" />
          ResearchGraph
        </Link>
        <ThemeToggle
          variant="circle"
          start="top-right"
          className="size-9 rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          iconClassName="size-4"
        />
      </div>
    </header>
  );
}
