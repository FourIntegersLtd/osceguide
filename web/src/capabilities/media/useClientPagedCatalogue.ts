"use client";

import { useState } from "react";
import { useAsync, type AsyncState } from "@/foundation/hooks";
import { listAllMedia, type MediaItem, type MediaKind } from "@/capabilities/media/api";
import { CLIENT_PAGE_SIZE, sortByTitle } from "@/capabilities/media/catalogue";

/**
 * A to Z and Podcasts read the whole catalogue once, sort it by title and show it ten at a time:
 * a later server page would sort in above the rows already on screen.
 *
 * `state` follows the one read; `rows` is the part shown so far, with "Load more" and a way to
 * show everything (a jump link to a letter beyond the shown rows needs the rest on the page).
 * `everything` is the full sorted catalogue, for what must not depend on how much is shown.
 */
export function useClientPagedCatalogue(kind: MediaKind, examCode: string | null | undefined) {
  const catalogue = useAsync(
    (signal) => listAllMedia(kind, signal, examCode).then(sortByTitle),
    [kind, examCode],
  );
  const [shown, setShown] = useState(CLIENT_PAGE_SIZE);
  const everything = catalogue.data ?? [];
  const items = everything.slice(0, shown);
  const state: AsyncState<MediaItem[]> = { ...catalogue, data: catalogue.data === null ? null : items };
  return {
    state,
    everything,
    rows: {
      items,
      hasMore: shown < everything.length,
      loadMore: () => setShown((count) => count + CLIENT_PAGE_SIZE),
      showAll: () => setShown(everything.length),
    },
  };
}
