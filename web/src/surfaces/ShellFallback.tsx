"use client";

import { Spinner } from "@/foundation/ui";

/** Shown while a code-split shell chunk loads. */
export function ShellFallback() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center bg-b2c-surface-muted">
      <Spinner label="Loading" />
    </div>
  );
}
