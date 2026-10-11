"use client";

import { FlaskConical, KeyRound, PlugZap } from "lucide-react";
import { useEffect, useState } from "react";

import { api, API_URL } from "@/lib/api";
import type { Health } from "@/lib/types";

type State = { kind: "loading" } | { kind: "ok"; health: Health } | { kind: "down" };

export function ServerStatus() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    api
      .health()
      .then((health) => setState({ kind: "ok", health }))
      .catch(() => setState({ kind: "down" }));
  }, []);

  if (state.kind === "loading") return null;
  if (state.kind === "down") {
    return (
      <Notice icon={<PlugZap className="size-3.5" />}>
        Can’t reach the research server at <code className="font-mono">{API_URL}</code>. Start the
        backend to begin.
      </Notice>
    );
  }
  if (state.health.demo) {
    return (
      <Notice icon={<FlaskConical className="size-3.5" />}>
        Demo mode: runs use placeholder data, not real research.
      </Notice>
    );
  }
  if (!state.health.configured) {
    return (
      <Notice icon={<KeyRound className="size-3.5" />}>
        The server has no API keys. Add them to <code className="font-mono">backend/.env</code>, or
        set <code className="font-mono">DEMO_MODE=true</code>.
      </Notice>
    );
  }
  return null;
}

function Notice({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <p className="mx-auto flex w-fit max-w-full items-center gap-2 rounded-full border bg-card px-3 py-1.5 text-xs text-muted-foreground">
      <span className="shrink-0 text-warning">{icon}</span>
      <span>{children}</span>
    </p>
  );
}
