"use client";

import { useCallback, useMemo, useState } from "react";
import { useAsync, type AsyncState } from "@/foundation/hooks";
import { useCurrentExam } from "@/foundation/session";
import { browseLibrary, type LibraryPage, type LibraryStation } from "@/capabilities/stations/api";

/** One page. Large enough that the client-side search has something to search. */
const PAGE_SIZE = 100;

/** Pages fetched after the first, and where the cursor got to. */
interface Paged {
  /** The filter these pages belong to. A different one throws them away. */
  key: string;
  items: LibraryStation[];
  cursor: string | null;
  /** False until "Load more" has been pressed, when the first page's cursor rules. */
  started: boolean;
}

export interface StationLibraryState {
  /** The first page, which owns the loading and failure states. */
  first: AsyncState<LibraryPage>;
  /** Everything fetched so far, filtered by the search term. */
  stations: LibraryStation[];
  /** Fetched but filtered out — so the empty state can say which kind of empty. */
  total: number;
  /** The exam being browsed. The app's, not this screen's — see `useCurrentExam`. */
  examCode: string | null;
  search: string;
  setSearch: (term: string) => void;
  hasMore: boolean;
  loadingMore: boolean;
  loadMore: () => void;
}

/**
 * Browsing the library: the search and the cursor, over one exam.
 *
 * The exam is the app's, not this screen's. This used to own an "All exams"
 * chip and one per published exam, which meant somebody browsing scenarios for
 * an exam they had never bought — the old client had one exam per deployment
 * and no such control at all. `GET /api/v1/stations` now refuses an exam the
 * caller may not open, so the chips would have been a row of buttons that
 * mostly 403.
 *
 * The search is applied here rather than sent, because that endpoint takes an
 * exam code and a cursor and nothing else. That is a real limit and it is
 * recorded in `docs/port-gaps.md`: a term only matches what has been paged in,
 * which is why "Load more" stays offered while one is typed.
 */
export function useStationLibrary(): StationLibraryState {
  const { code: examCode, loading: examLoading } = useCurrentExam();
  const [search, setSearch] = useState("");
  const [loadingMore, setLoadingMore] = useState(false);

  const first = useAsync(
    // Nothing to browse until the exam is known. Asking without one would ask
    // the server to choose, and it would choose right — but the page would then
    // show a different exam's stations for one frame.
    (signal) =>
      examCode
        ? browseLibrary({ examCode, limit: PAGE_SIZE }, signal)
        : Promise.resolve({ items: [], next_cursor: null } as LibraryPage),
    [examCode],
  );

  const key = examCode ?? "";
  const [paged, setPaged] = useState<Paged>({ key, items: [], cursor: null, started: false });
  // A different filter is a different list. Reset during render rather than in
  // an effect: an effect would paint one frame of the old exam's stations
  // under the new exam's chip.
  if (paged.key !== key) setPaged({ key, items: [], cursor: null, started: false });

  const cursor = paged.started ? paged.cursor : (first.data?.next_cursor ?? null);

  const loadMore = useCallback(() => {
    if (!cursor || loadingMore) return;
    setLoadingMore(true);
    browseLibrary({ examCode, cursor, limit: PAGE_SIZE })
      .then((page) => {
        setPaged((current) =>
          current.key !== key
            ? current
            : {
                key,
                items: [...current.items, ...page.items],
                cursor: page.next_cursor ?? null,
                started: true,
              },
        );
      })
      .catch(() => {
        // The pages already on screen still stand. Stopping the cursor is the
        // honest outcome: the button goes rather than offering a retry that
        // would loop against the same failure.
        setPaged((current) => ({ ...current, cursor: null, started: true }));
      })
      .finally(() => setLoadingMore(false));
  }, [cursor, examCode, key, loadingMore]);

  const loaded = useMemo(
    () => [...(first.data?.items ?? []), ...(paged.key === key ? paged.items : [])],
    [first.data, paged, key],
  );

  const stations = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return loaded;
    return loaded.filter((station) => station.title.toLowerCase().includes(term));
  }, [loaded, search]);

  return {
    first: examLoading ? { ...first, loading: true } : first,
    stations,
    total: loaded.length,
    examCode,
    search,
    setSearch,
    hasMore: cursor !== null,
    loadingMore,
    loadMore,
  };
}
