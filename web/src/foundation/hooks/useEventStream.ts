"use client";

import { useEffect, useRef, useState } from "react";
import { listenForSnapshots, streamUrl } from "./eventStreamProtocol";
import { mintStreamTicket, platformApiUrl } from "@/foundation/platform-client";

export interface EventStreamState<T> {
  /** The most recent payload the server pushed. */
  data: T | null;
  connected: boolean;
  error: Error | null;
}

/**
 * Subscribe to a server-sent event stream.
 *
 * Replaces polling: the old institution console re-fetched circuit state every
 * eight seconds, which was both slow to show a change and a steady load for
 * every open tab in an exam hall.
 *
 * A ticket is minted per connection because `EventSource` cannot send headers.
 * On a drop the browser reconnects on its own, but a ticket is single-use and
 * short-lived, so this remounts the source with a fresh one instead.
 */
export function useEventStream<T>(
  path: string | null,
  { enabled = true }: { enabled?: boolean } = {},
): EventStreamState<T> {
  const [data, setData] = useState<T | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [generation, setGeneration] = useState(0);
  const retryRef = useRef(0);

  useEffect(() => {
    if (!path || !enabled) return;
    let source: EventSource | null = null;
    let stopListening: (() => void) | undefined;
    let retryTimer: number | undefined;
    let live = true;

    (async () => {
      try {
        const ticket = await mintStreamTicket();
        if (!live) return;
        source = new EventSource(streamUrl(platformApiUrl(), path, window.location.origin, ticket));

        source.onopen = () => {
          if (!live) return;
          setConnected(true);
          setError(null);
          retryRef.current = 0;
        };

        stopListening = listenForSnapshots<T>(source, (snapshot) => {
          if (live) setData(snapshot);
        });

        source.onerror = () => {
          if (!live) return;
          setConnected(false);
          source?.close();
          // Backs off to a ceiling: an exam hall reconnecting in lockstep after
          // a blip is a thundering herd on the one endpoint that matters.
          const delay = Math.min(30_000, 1_000 * 2 ** retryRef.current);
          retryRef.current += 1;
          retryTimer = window.setTimeout(() => setGeneration((n) => n + 1), delay);
        };
      } catch (cause) {
        if (!live) return;
        setConnected(false);
        setError(cause instanceof Error ? cause : new Error(String(cause)));
        const delay = Math.min(30_000, 1_000 * 2 ** retryRef.current);
        retryRef.current += 1;
        retryTimer = window.setTimeout(() => setGeneration((n) => n + 1), delay);
      }
    })();

    return () => {
      live = false;
      stopListening?.();
      source?.close();
      if (retryTimer) window.clearTimeout(retryTimer);
    };
  }, [path, enabled, generation]);

  return { data, connected, error };
}
