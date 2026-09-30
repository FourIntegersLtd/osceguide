"use client";

import { Alert, Button } from "@/foundation/ui";

/**
 * A section that failed to load, with its retry.
 *
 * Says in words that nothing is zero: a dashboard that draws a failure as an
 * empty chart tells a partner they had no sign-ups.
 */
export function LoadFailure({
  title,
  error,
  onRetry,
  note = "Nothing here is zero; it just hasn't loaded.",
}: {
  title: string;
  error: Error;
  onRetry: () => void;
  note?: string;
}) {
  return (
    <Alert tone="danger" title={title}>
      <p>
        {error.message} {note}
      </p>
      <div className="mt-3">
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Try again
        </Button>
      </div>
    </Alert>
  );
}
