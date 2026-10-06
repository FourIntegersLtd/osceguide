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
 *
 * `holdOnSuccess` keeps `busy` set after a successful run, for an action that
 * ends in a navigation: clearing it while the router is still moving lets a
 * second click start the work again.
 */
export function useAction(onDone?: () => void, { holdOnSuccess = false }: { holdOnSuccess?: boolean } = {}): ActionState {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(
    async (key: string, work: () => Promise<unknown>) => {
      setBusy(key);
      setError(null);
      try {
        await work();
        onDone?.();
        if (!holdOnSuccess) setBusy(null);
        return true;
      } catch (cause) {
        setError(errorMessage(cause));
        setBusy(null);
        return false;
      }
    },
    [onDone, holdOnSuccess],
  );

  return { busy, error, clearError: () => setError(null), run };
}
