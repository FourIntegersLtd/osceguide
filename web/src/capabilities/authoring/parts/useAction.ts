"use client";

import { useCallback, useState } from "react";
import { errorMessage } from "@/foundation/hooks";

export interface ActionState {
  /** The key of the row currently running, or null. */
  busy: string | null;
  error: string | null;
  clearError: () => void;
  run: (key: string, work: () => Promise<unknown>) => Promise<boolean>;
}

/**
 * One row action at a time, with the failure kept.
 *
 * Publishing, archiving and deleting all read the same in the old screens: the
 * button says "Publishing…", and a failure becomes a dismissible alert above
 * the list rather than a swallowed console error. Keeping that in one hook is
 * what stops the three sections drifting apart the way the three trees did.
 */
export function useAction(onDone?: () => void): ActionState {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(
    async (key: string, work: () => Promise<unknown>) => {
      setBusy(key);
      setError(null);
      try {
        await work();
        onDone?.();
        return true;
      } catch (cause) {
        setError(errorMessage(cause));
        return false;
      } finally {
        setBusy(null);
      }
    },
    [onDone],
  );

  return { busy, error, clearError: () => setError(null), run };
}
