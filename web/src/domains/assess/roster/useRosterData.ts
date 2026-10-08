"use client";

import { useRef } from "react";
import { useAsync } from "@/foundation/hooks/useAsync";
import type { Trainee } from "@/domains/assess/api";
import {
  listAllTrainees,
  listCohorts,
  listTraineeGroups,
  type Cohort,
  type TraineeGroup,
} from "@/domains/assess/roster/api";

export interface RosterData {
  trainees: Trainee[];
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
          trainees: () => listAllTrainees(orgSlug, signal),
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
  return { state, reloadAfter };
}
