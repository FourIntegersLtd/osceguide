"use client";

import { useEffect } from "react";

/**
 * Tells a host (the Settings tab strip) whether this panel holds unsaved edits, and clears it
 * when the panel goes away, so a closed form never leaves the "Leave without saving?" guard armed.
 */
export function useDirtyGuard(dirty: boolean, setDirty: (dirty: boolean) => void): void {
  useEffect(() => {
    setDirty(dirty);
    return () => setDirty(false);
  }, [dirty, setDirty]);
}
