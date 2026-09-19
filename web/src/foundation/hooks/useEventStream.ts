"use client";

import { useEffect, useRef, useState } from "react";
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
    let retryTimer: number | undefined;
    let live = true;

    (async () => {
      try {
        const ticket = await mintStreamTicket();
        if (!live) return;
        const url = new URL(`${platformApiUrl()}${path}`);
        url.searchParams.set("ticket", ticket);
        source = new EventSource(url.toString());

        source.onopen = () => {
          if (!live) return;
          setConnected(true);
          setError(null);
          retryRef.current = 0;
        };

        source.onmessage = (event) => {
          if (!live) return;
          try {
            setData(JSON.parse(event.data) as T);
          } catch {
            // A keep-alive comment or a frame we do not understand. Dropping it
            // is right; throwing would tear down a working stream.
          }
        };

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
        if (live) setError(cause instanceof Error ? cause : new Error(String(cause)));
      }
    })();

    return () => {
      live = false;
      source?.close();
      if (retryTimer) window.clearTimeout(retryTimer);
    };
  }, [path, enabled, generation]);

  return { data, connected, error };
}
