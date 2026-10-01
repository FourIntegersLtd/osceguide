"use client";

import { useCallback, useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  dateRangeForPreset,
  parseAttributionFilters,
  toAttributionQuery,
  type ConcreteRangePreset,
} from "@/capabilities/attribution-dashboard/presets";
import {
  parseAttributionTab,
  type AttributionTab,
} from "@/capabilities/attribution-dashboard/tabs";
import type {
  AttributionFilters,
  AttributionMode,
  AttributionQuery,
} from "@/capabilities/attribution-dashboard/types";

/**
 * The dashboard's filters and tab, kept in the URL.
 *
 * Reloading or sharing a link keeps the range, exam and tab; nothing is held in
 * component state, so the request the page makes is always the one the address
 * describes. A reporter passes `lockedPartner`, which no query string can change.
 */
export function useAttributionState(mode: AttributionMode, lockedPartner?: string) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const filters = useMemo(
    () => parseAttributionFilters(searchParams, lockedPartner),
    [searchParams, lockedPartner],
  );
  const query = useMemo<AttributionQuery>(() => toAttributionQuery(filters), [filters]);
  const tab = useMemo(
    () => parseAttributionTab(searchParams.get("tab"), mode),
    [searchParams, mode],
  );

  const replaceParams = useCallback(
    (edit: (params: URLSearchParams) => void) => {
      const params = new URLSearchParams(searchParams.toString());
      edit(params);
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  const setFilters = useCallback(
    (next: Partial<AttributionFilters>) => {
      const merged: AttributionFilters = {
        ...filters,
        ...next,
        partner: lockedPartner ?? next.partner ?? filters.partner,
      };
      replaceParams((params) => {
        params.set("from_date", merged.fromDate);
        params.set("to_date", merged.toDate);
        params.set("partner", merged.partner);
        if (merged.exam) params.set("exam", merged.exam);
        else params.delete("exam");
        if (merged.utmCampaign) params.set("utm_campaign", merged.utmCampaign);
        else params.delete("utm_campaign");
      });
    },
    [filters, lockedPartner, replaceParams],
  );

  const selectPreset = useCallback(
    (preset: ConcreteRangePreset) => setFilters(dateRangeForPreset(preset)),
    [setFilters],
  );

  const reset = useCallback(
    () => setFilters({ ...dateRangeForPreset("this_month"), exam: "", utmCampaign: "" }),
    [setFilters],
  );

  const setTab = useCallback(
    (next: AttributionTab) => replaceParams((params) => params.set("tab", next)),
    [replaceParams],
  );

  return { filters, query, tab, setFilters, selectPreset, reset, setTab };
}
