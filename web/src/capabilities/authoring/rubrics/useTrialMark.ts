"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { errorMessage } from "@/foundation/hooks";
import {
  trialMarkRubricVersion,
  type AuthoringScope,
  type TrialMark,
  type TrialMarkRequest,
} from "@/capabilities/authoring/api";

export interface TrialMarkState {
  /** The latest snapshot the stream sent: `marking` while it runs, then `marked` or `failed`. */
  snapshot: TrialMark | null;
  running: boolean;
  /** A refusal before the stream opened, or a dropped connection, in words. */
  error: string | null;
  start: (version: number, body: TrialMarkRequest) => Promise<void>;
  cancel: () => void;
}

/**
 * One trial mark at a time, streamed.
 *
 * The backend answers a trial with server-sent events: a `marking` snapshot
 * every few seconds and then the finished one. This keeps the latest, so the
 * panel can show "Marking… 14 s" and then the result, without polling.
 * Starting again, or leaving the screen, aborts the stream in flight.
 */
export function useTrialMark(scope: AuthoringScope, rubricId: string): TrialMarkState {
  const [snapshot, setSnapshot] = useState<TrialMark | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(() => () => controllerRef.current?.abort(), []);

  const cancel = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
    setRunning(false);
  }, []);

  const start = useCallback(
    async (version: number, body: TrialMarkRequest) => {
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
      setSnapshot(null);
      setError(null);
      setRunning(true);
      try {
        await trialMarkRubricVersion(scope, rubricId, version, body, setSnapshot, controller.signal);
      } catch (cause) {
        if (!controller.signal.aborted) setError(errorMessage(cause));
      } finally {
        if (controllerRef.current === controller) {
          controllerRef.current = null;
          setRunning(false);
        }
      }
    },
    [scope, rubricId],
  );

  return { snapshot, running, error, start, cancel };
}
