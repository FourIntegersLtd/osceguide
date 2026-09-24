"use client";

import { useCallback, useMemo, useState } from "react";
import { useAsync, type AsyncState } from "@/foundation/hooks";
import { useCurrentExam } from "@/foundation/session";
import { browseLibrary, type LibraryPage, type LibraryStation } from "@/capabilities/stations/api";

/** The most the library endpoint will answer in one page; more is a 422. */
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
  /** Everything fetched for the applied filter, in the server's order. */
  stations: LibraryStation[];
  /** The term actually sent. Empty means the whole exam. */
  applied: string;
  /** The exam being browsed. The app's, not this screen's — see `useCurrentExam`. */
  examCode: string | null;
  /** What is in the box, which is not yet what is being searched for. */
  search: string;
  setSearch: (term: string) => void;
  /** Send what is typed. The search is submitted, not typed — see below. */
  applySearch: () => void;
  /** Drop the term and the pages that were fetched under it. */
  clearSearch: () => void;
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
 * The term is sent, not applied here. It used to be filtered over whatever had
 * been paged in, because the endpoint took an exam code and a cursor and
 * nothing else; `?search=` matches a title fragment in SQL now, so "nothing
 * matches" means the library, not the part of it that arrived first. The page
 * is refetched from the top under a new term — a cursor into the unfiltered
 * list is not a cursor into the filtered one — and a term is committed on
 * submit rather than on every keystroke, which is how the retiring client's
 * list searched and how `capabilities/media` still does: one request per thing
 * somebody meant, not one per letter.
 */
export function useStationLibrary(): StationLibraryState {
  const { code: examCode, loading: examLoading } = useCurrentExam();
  const [search, setSearchTerm] = useState("");
  const [applied, setApplied] = useState("");
  const [loadingMore, setLoadingMore] = useState(false);

  const first = useAsync(
    // Nothing to browse until the exam is known. Asking without one would ask
    // the server to choose, and it would choose right — but the page would then
    // show a different exam's stations for one frame.
    (signal) =>
      examCode
        ? browseLibrary({ examCode, search: applied, limit: PAGE_SIZE }, signal)
        : Promise.resolve({ items: [], next_cursor: null } as LibraryPage),
    [examCode, applied],
  );

  const key = `${examCode ?? ""}|${applied}`;
  const [paged, setPaged] = useState<Paged>({ key, items: [], cursor: null, started: false });
  // A different filter is a different list. Reset during render rather than in
  // an effect: an effect would paint one frame of the old exam's stations
  // under the new exam's chip.
  if (paged.key !== key) setPaged({ key, items: [], cursor: null, started: false });

  const cursor = paged.started ? paged.cursor : (first.data?.next_cursor ?? null);

  const loadMore = useCallback(() => {
    // Also refused while the first page of the current filter is still coming
    // in: the only cursor to hand is then the previous filter's, and a cursor
    // out of the unfiltered list is not a cursor into the filtered one.
    if (!cursor || loadingMore || first.loading) return;
    setLoadingMore(true);
    browseLibrary({ examCode, search: applied, cursor, limit: PAGE_SIZE })
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
  }, [applied, cursor, examCode, first.loading, key, loadingMore]);

  const setSearch = useCallback((term: string) => {
    setSearchTerm(term);
    // Emptying the box is not a draft search — it is the request to stop
    // filtering, and the native ✕ in a `type="search"` control writes exactly
    // that without ever going near the submit button.
    if (term === "") setApplied("");
  }, []);

  const applySearch = useCallback(() => setApplied(search.trim()), [search]);

  const clearSearch = useCallback(() => {
    setSearchTerm("");
    setApplied("");
  }, []);

  const stations = useMemo(
    () => [...(first.data?.items ?? []), ...(paged.key === key ? paged.items : [])],
    [first.data, paged, key],
  );

  return {
    first: examLoading ? { ...first, loading: true } : first,
    stations,
    applied,
    examCode,
    search,
    setSearch,
    applySearch,
    clearSearch,
    // Withdrawn while a new term's first page is on the wire, for the same
    // reason `loadMore` refuses then.
    hasMore: cursor !== null && !first.loading,
    loadingMore,
    loadMore,
  };
}
