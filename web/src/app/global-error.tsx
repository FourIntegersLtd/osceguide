"use client";

import { useEffect } from "react";
import { reportError } from "@/foundation/observability";

/**
 * The root layout itself threw, so `error.tsx` (which renders inside it) cannot.
 *
 * Replaces the whole document, which is why it draws its own `<html>` and
 * carries no app styles it could depend on. Reported like any other boundary.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    reportError(error, error.digest ? { digest: error.digest } : undefined);
  }, [error]);

  return (
    <html lang="en">
      <body style={{ fontFamily: "system-ui, sans-serif", padding: "4rem 1rem", textAlign: "center" }}>
        <h1 style={{ fontSize: "1.25rem" }}>Something went wrong</h1>
        <p>The page could not be shown. Trying again often works.</p>
        {error.digest ? <p style={{ fontFamily: "monospace" }}>Reference {error.digest}</p> : null}
        <button type="button" onClick={reset}>
          Try again
        </button>
      </body>
    </html>
  );
}
