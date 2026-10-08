"use client";

import { useCallback, useEffect, useState } from "react";
import { readUnreadCount } from "@/capabilities/inbox/api";

export interface InboxUnread {
  /** Zero until the first answer; the badge simply stays hidden if the read fails. */
  count: number;
  refresh: () => void;
  decrement: () => void;
  clear: () => void;
}

/**
 * The unread count the shell shows. Fetched once, and again whenever the
 * server says a message arrived (or the stream reconnected). `enabled` is
 * false on arms with no inbox, which then never make the request.
 */
export function useInboxUnread(enabled: boolean): InboxUnread {
  const [count, setCount] = useState(0);

  const refresh = useCallback(() => {
    if (!enabled) return;
    readUnreadCount()
      .then(setCount)
      .catch(() => undefined);
  }, [enabled]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const decrement = useCallback(() => setCount((n) => Math.max(0, n - 1)), []);
  const clear = useCallback(() => setCount(0), []);
  return { count, refresh, decrement, clear };
}
