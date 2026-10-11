"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { PlaceholdersAndVanishInput } from "@/components/ui/placeholders-and-vanish-input";
import { api } from "@/lib/api";

const EXAMPLES = [
  "Does a four-day work week improve productivity?",
  "How effective are carbon capture technologies at scale?",
  "Is intermittent fasting better than calorie restriction for weight loss?",
  "What is the evidence that microplastics harm human health?",
  "Do electric vehicles have lower lifetime emissions than petrol cars?",
];

export function QuestionForm() {
  const router = useRouter();
  const [pending, setPending] = useState(false);

  async function start(question: string) {
    if (pending) return;
    setPending(true);
    try {
      const run = await api.createRun(question);
      router.push(`/research/${run.id}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not start research.");
      setPending(false);
    }
  }

  return (
    <div className="w-full">
      <PlaceholdersAndVanishInput
        placeholders={EXAMPLES}
        onSubmit={start}
        disabled={pending}
        ariaLabel="What do you want to research?"
      />
      <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
        <span className="text-xs text-muted-foreground">Try</span>
        {EXAMPLES.slice(0, 3).map((example) => (
          <button
            key={example}
            type="button"
            disabled={pending}
            onClick={() => start(example)}
            className="max-w-full truncate rounded-full border bg-card/60 px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-foreground/20 hover:text-foreground disabled:opacity-50"
          >
            {example}
          </button>
        ))}
      </div>
    </div>
  );
}
