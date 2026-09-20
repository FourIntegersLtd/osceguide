"use client";

import { useCallback } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import type { StationAction } from "@/domains/train/station/useStationAttempt";
import type { StationStep } from "@/domains/train/station/StationChrome";

/** Keeps the retiring client's query-string shape for the four station steps. */
export function useStationUrl() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const replace = useCallback(
    (patch: { step?: StationStep; action?: StationAction; attemptId?: string | null }) => {
      const params = new URLSearchParams(searchParams.toString());
      if (patch.step) params.set("tab", patch.step);
      if (patch.action) params.set("action", patch.action);
      if (patch.attemptId) params.set("attempt", patch.attemptId);
      else if (patch.attemptId === null) params.delete("attempt");
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  return { replace };
}
