"use client";

import { useCallback, useRef, useState } from "react";
import { useAsync, type AsyncState } from "@/foundation/hooks";

export interface CursorPage<T> {
  items: T[];
  next_cursor?: string | null;
}

export interface CursorPages<T> {
  /** The first page, through `useAsync`, so a failure to load is a failure. */
  state: AsyncState<T[]>;
  /** Whether the server said there is more. */
  hasMore: boolean;
  loadingMore: boolean;
  /** A failed "load more", kept so it is shown rather than read as the end. */
  moreError: Error | null;
  loadMore: () => void;
}

/**
 * A list read one server page at a time, growing on request.
 *
 * Replaces walking every cursor up front: the catalogue used to load 25 pages
 * of 100 before drawing a row, and silently stopped at 2,500. Changing `deps`
 * (a search, a scope) starts again from the first page.
 */
export function useCursorPages<T>(
  load: (cursor: string | null, signal: AbortSignal) => Promise<CursorPage<T>>,
  deps: readonly unknown[],
): CursorPages<T> {
  const [cursor, setCursor] = useState<string | null>(null);
  const [extra, setExtra] = useState<T[]>([]);
  const [loadingMore, setLoadingMore] = useState(false);
  const [moreError, setMoreError] = useState<Error | null>(null);
  const loadRef = useRef(load);
  loadRef.current = load;
  // Bumped on every restart, so a "load more" answering after the list was
  // reset (a new search) cannot append to the wrong list.
  const generation = useRef(0);

  const first = useAsync(
    async (signal) => {
      generation.current += 1;
      setExtra([]);
      setMoreError(null);
      setLoadingMore(false);
      const page = await loadRef.current(null, signal);
      setCursor(page.next_cursor ?? null);
      return page.items;
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    deps,
  );

  const loadMore = useCallback(() => {
    if (!cursor || loadingMore) return;
    const at = generation.current;
    setLoadingMore(true);
    setMoreError(null);
    loadRef
      .current(cursor, new AbortController().signal)
      .then((page) => {
        if (at !== generation.current) return;
        setExtra((previous) => [...previous, ...page.items]);
        setCursor(page.next_cursor ?? null);
      })
      .catch((cause: unknown) => {
        if (at !== generation.current) return;
        setMoreError(cause instanceof Error ? cause : new Error(String(cause)));
      })
      .finally(() => {
        if (at === generation.current) setLoadingMore(false);
      });
  }, [cursor, loadingMore]);

  const items = first.data === null ? null : [...first.data, ...extra];
  return {
    state: { ...first, data: items },
    hasMore: first.data !== null && cursor !== null,
    loadingMore,
    moreError,
    loadMore,
  };
}
