"use client";

import { useCallback, useEffect } from "react";
import { useMeEvents, type MeEvent, type MeEventName } from "@/foundation/hooks/useMeEvents";

/**
 * Read once on mount and again when `/me/events` says something relevant changed, or on `resync`.
 * Failed reads are ignored so the next wake can try again — the pattern behind marking, feedback
 * and debrief waits (nothing polls).
 */
export function useEventDrivenReconcile({
  enabled,
  topics,
  matches,
  reconcile,
}: {
  enabled: boolean;
  topics: MeEventName[];
  matches: (event: MeEvent) => boolean;
  reconcile: () => void | Promise<void>;
}): void {
  const run = useCallback(async () => {
    try {
      await reconcile();
    } catch {
      // a failed read is not an outcome; the next event asks again
    }
  }, [reconcile]);

  useEffect(() => {
    if (enabled) void run();
  }, [enabled, run]);

  useMeEvents(topics, (event) => {
    if (!enabled) return;
    if (event.name === "resync" || matches(event)) void run();
  });
}
