"use client";

import { useRef, useState } from "react";
import { useAsync } from "@/foundation/hooks/useAsync";
import type { Trainee } from "@/domains/assess/api";
import { errorMessage } from "@/foundation/hooks/useAsync";
import {
  listCohorts,
  readTraineeSlice,
  listTraineeGroups,
  type Cohort,
  type TraineeSlice,
  type TraineeGroup,
} from "@/domains/assess/roster/api";

export interface RosterData {
  /** The first page and the roster's full size; `useRosterData` grows it on request. */
  trainees: TraineeSlice;
  cohorts: Cohort[];
  groups: TraineeGroup[];
}

export type RosterPart = keyof RosterData;

const ALL_PARTS: readonly RosterPart[] = ["trainees", "cohorts", "groups"];

/**
 * Load the roster screen's three lists, refetching only the ones marked stale.
 *
 * A write changes one or two of them; the whole roster is paged cursor by cursor, so
 * refetching it for a group rename is the expensive way to be sure. A different
 * organisation discards the cache. Exported for its test; the screen uses `useRosterData`.
 */
export async function loadRoster(
  cache: { slug?: string; data?: RosterData },
  slug: string,
  stale: ReadonlySet<RosterPart>,
  fetchers: { [K in RosterPart]: () => Promise<RosterData[K]> },
): Promise<RosterData> {
  const previous = cache.slug === slug ? cache.data : undefined;
  const pick = async <K extends RosterPart>(part: K): Promise<RosterData[K]> =>
    previous && !stale.has(part) ? previous[part] : fetchers[part]();
  const [trainees, cohorts, groups] = await Promise.all([pick("trainees"), pick("cohorts"), pick("groups")]);
  cache.slug = slug;
  cache.data = { trainees, cohorts, groups };
  return cache.data;
}

/**
 * The roster's three lists, and `reloadAfter(...parts)`: a handler that refetches just those
 * (a write that changed a group's count passes "groups", not the whole roster).
 *
 * The first load reads one page of trainees and the total; `trainees` is what has been loaded
 * so far and `loadMore` reads the next page, for the tabs that need to pick from everyone.
 */
export function useRosterData(orgSlug: string) {
  const cache = useRef<{ slug?: string; data?: RosterData }>({});
  const stale = useRef<Set<RosterPart>>(new Set(ALL_PARTS));
  const state = useAsync(
    async (signal) => {
      const parts = stale.current;
      stale.current = new Set();
      try {
        return await loadRoster(cache.current, orgSlug, parts, {
          trainees: () => readTraineeSlice(orgSlug, signal),
          cohorts: async () => (await listCohorts(orgSlug, signal)).items,
          groups: async () => (await listTraineeGroups(orgSlug, signal)).items,
        });
      } catch (cause) {
        // Nothing was cached, so the next attempt must fetch what this one meant to.
        parts.forEach((part) => stale.current.add(part));
        throw cause;
      }
    },
    [orgSlug],
  );
  const reloadAfter =
    (...parts: RosterPart[]) =>
    () => {
      parts.forEach((part) => stale.current.add(part));
      state.reload();
    };
  const first = state.data?.trainees;
  // Rows appended to one first page; a reload hands back a new first page, which makes them stale.
  const [grown, setGrown] = useState<{ base: TraineeSlice | undefined; rows: Trainee[]; cursor: string | null } | null>(null);
  const extra = grown && grown.base === first ? grown : null;
  const [loadingMore, setLoadingMore] = useState(false);
  const [moreError, setMoreError] = useState<Error | null>(null);
  const cursor = extra ? extra.cursor : (first?.cursor ?? null);
  const loadMore = () => {
    if (!cursor || loadingMore) return;
    setLoadingMore(true);
    setMoreError(null);
    readTraineeSlice(orgSlug, undefined, cursor)
      .then((page) => setGrown({ base: first, rows: [...(extra?.rows ?? []), ...page.rows], cursor: page.cursor }))
      .catch((cause: unknown) => setMoreError(new Error(errorMessage(cause))))
      .finally(() => setLoadingMore(false));
  };
  const trainees = { rows: [...(first?.rows ?? []), ...(extra?.rows ?? [])], total: first?.total ?? 0 };
  return { state, reloadAfter, trainees, hasMore: cursor !== null, loadMore, loadingMore, moreError };
}
