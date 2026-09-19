"use client";

import { useEffect } from "react";
import { Button } from "@/foundation/ui";

/**
 * Something threw while rendering.
 *
 * Deliberately plain and deliberately not chatty about the cause: a stack
 * trace on a candidate's screen mid-exam is worse than a sentence and a way
 * forward. The digest is shown because it is the one thing support can ask for
 * that makes the server log findable.
 */
export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-md text-center">
        <h1 className="text-lg font-semibold text-ink">Something went wrong</h1>
        <p className="mt-2 text-sm text-ink-muted">
          The page could not be shown. Trying again often works; if it does not, the reference
          below will tell us where to look.
        </p>
        {error.digest && (
          <p className="mt-3 font-mono text-xs text-ink-subtle">Reference {error.digest}</p>
        )}
        <Button className="mt-5" onClick={reset}>
          Try again
        </Button>
      </div>
    </main>
  );
}
