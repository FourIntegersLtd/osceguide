"use client";

import { useCallback, useEffect, useState } from "react";

/** Each signed-in user and audience owns a separate persisted entry. */
export function useQueuePersistence(scope: string | null) {
  const key = scope ? `peer_practice_queue_${scope}` : null;
  const [entryId, setEntryId] = useState<string | null>(null);
  useEffect(() => {
    const restore = () => {
      try { setEntryId(key ? localStorage.getItem(key) : null); }
      catch { setEntryId(null); }
    };
    restore();
    const sync = (event: StorageEvent) => {
      if (event.key === key || event.key === null) restore();
    };
    window.addEventListener("storage", sync);
    return () => window.removeEventListener("storage", sync);
  }, [key]);
  const remember = useCallback((id: string | null) => {
    if (!key) return;
    try {
      if (id) localStorage.setItem(key, id);
      else localStorage.removeItem(key);
    } catch { /* Storage may be unavailable; the in-memory queue still works. */ }
    setEntryId(id);
  }, [key]);
  return { entryId, remember };
}
