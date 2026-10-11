"use client";

import { useEffect, useReducer, useState } from "react";

import { api } from "@/lib/api";
import { initialView, reduceView } from "@/lib/research-state";
import { TERMINAL_EVENTS, type RunEvent } from "@/lib/types";

export type Connection = "open" | "reconnecting" | "lost";

/**
 * Subscribes to a run's Server-Sent Events and folds them into view state.
 *
 * The server replays every stored event first, so this works the same for a
 * live run, a refresh mid-run, or a finished run opened from history.
 * EventSource reconnects on its own and resumes via Last-Event-ID; we close it
 * once a terminal event arrives so it doesn't reconnect forever.
 *
 * State is per mount: callers key the consuming component by run id, so a new
 * run gets a fresh reducer instead of a reset inside the effect.
 */
export function useResearchRun(id: string) {
  const [view, dispatch] = useReducer(reduceView, initialView);
  const [connection, setConnection] = useState<Connection>("open");

  useEffect(() => {
    const source = new EventSource(api.eventsUrl(id));
    let finished = false;

    source.onopen = () => setConnection("open");
    source.onmessage = (message) => {
      const event = JSON.parse(message.data) as RunEvent;
      dispatch(event);
      if (TERMINAL_EVENTS.has(event.type)) {
        finished = true;
        source.close();
      }
    };
    source.onerror = () => {
      if (finished) return;
      setConnection(source.readyState === EventSource.CLOSED ? "lost" : "reconnecting");
    };
    return () => source.close();
  }, [id]);

  return { view, connection };
}
