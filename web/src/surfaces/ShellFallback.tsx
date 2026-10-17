"use client";

import { PageSpinner } from "@/foundation/ui";

/** Shown while a code-split shell chunk loads. */
export function ShellFallback() {
  return (
    <PageSpinner fill="section" className="min-h-[50vh] bg-b2c-surface-muted" />
  );
}
