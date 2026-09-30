"use client";

import { useEffect } from "react";
import { recordActivity, type ActivityIn } from "@/capabilities/account/api";

/**
 * Record that this page was opened, once per item.
 *
 * Pass `null` until the item has loaded (or when it is locked). The event is
 * compared by value, so a parent that rebuilds the same object every render
 * still posts once.
 */
export function useRecordView(event: ActivityIn | null): void {
  const serialised = event ? JSON.stringify(event) : null;
  useEffect(() => {
    if (serialised) void recordActivity(JSON.parse(serialised) as ActivityIn);
  }, [serialised]);
}
