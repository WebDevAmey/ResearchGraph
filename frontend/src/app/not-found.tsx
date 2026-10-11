import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="mx-auto flex max-w-md flex-1 flex-col items-center justify-center px-6 py-24 text-center">
      <p className="font-mono text-xs text-muted-foreground">404</p>
      <h1 className="mt-2 font-serif text-3xl">Nothing here</h1>
      <p className="mt-2 text-sm text-muted-foreground">This page doesn’t exist.</p>
      <Button asChild size="sm" className="mt-6">
        <Link href="/">Back to ResearchGraph</Link>
      </Button>
    </div>
  );
}
