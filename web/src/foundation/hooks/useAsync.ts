"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { PlatformError, PlatformTransportError } from "@/foundation/platform-client";

export interface AsyncState<T> {
  data: T | null;
  error: Error | null;
  loading: boolean;
  /** Re-run the loader. Safe to pass straight to a retry button. */
  reload: () => void;
}

/**
 * Load something from the API, once, with the failure kept.
 *
 * The consumer UX audit found ~173 `catch { console.error }` sites that set no
 * UI state, so a failed fetch rendered as "no data" — on a partner's own
 * dashboard, a network error read as "no sign-ups in this range". Every screen
 * here goes through this hook so a failure is always a failure.
 *
 * `deps` behaves like an effect dependency list: change it and the loader runs
 * again with the previous result discarded.
 */
export function useAsync<T>(
  loader: (signal: AbortSignal) => Promise<T>,
  deps: readonly unknown[] = [],
): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);
  const [nonce, setNonce] = useState(0);
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  useEffect(() => {
    const controller = new AbortController();
    let live = true;
    setLoading(true);
    setError(null);

    loaderRef
      .current(controller.signal)
      .then((result) => {
        if (!live) return;
        setData(result);
        setError(null);
      })
      .catch((cause: unknown) => {
        if (!live || controller.signal.aborted) return;
        setData(null);
        setError(asError(cause));
      })
      .finally(() => {
        if (live) setLoading(false);
      });

    return () => {
      live = false;
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  return { data, error, loading, reload };
}

function asError(cause: unknown): Error {
  if (cause instanceof PlatformError || cause instanceof PlatformTransportError) return cause;
  if (cause instanceof Error) return cause;
  return new Error(String(cause));
}

/** The sentence to show a person for a failure. Never the raw exception. */
/**
 * What to show a person when something failed.
 *
 * Takes `unknown` because that is what a `catch` binding is, and a helper
 * whose whole purpose is handling failure should not make its callers narrow
 * the type first.
 */
export function errorMessage(error: unknown): string {
  if (!error) return "";
  if (error instanceof PlatformTransportError) {
    return "We could not reach the server. Check your connection and try again.";
  }
  if (error instanceof PlatformError) return error.message;
  return "Something went wrong. Please try again.";
}
