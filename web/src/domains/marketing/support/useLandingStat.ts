"use client";

import { useEffect, useState } from "react";
import { fetchLandingStats, type LandingStats } from "@/domains/marketing/support/landingStats";

/** One site statistic, or null until it loads, when it fails, and when it is not above zero. */
export function useLandingStat(field: keyof Omit<LandingStats, "as_of">): number | null {
  const [value, setValue] = useState<number | null>(null);
  useEffect(() => {
    let alive = true;
    void fetchLandingStats().then((stats) => {
      const n = Number(stats?.[field] ?? 0);
      if (alive) setValue(n > 0 ? n : null);
    });
    return () => {
      alive = false;
    };
  }, [field]);
  return value;
}
