"use client";

import { useCallback } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import type { StationAction } from "@/capabilities/station-runner/useStationAttempt";
import type { StationStep } from "@/capabilities/station-runner/StationChrome";

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

/**
 * The step a `tab` param names, or nothing.
 *
 * Reading is the other half of `replace` above, so it lives beside it: the
 * query shape is this capability's, and an arm that guessed at it would drift
 * the moment a fifth step appeared. An unrecognised value is *absent* rather
 * than a default, because the screen then decides what the station is on.
 */
export function stationStepFromParam(value: string | undefined): StationStep | undefined {
  return value === "patient" ||
    value === "simulation" ||
    value === "management" ||
    value === "feedback"
    ? value
    : undefined;
}

/** Whether the URL is sitting the station or reading it back after. */
export function stationActionFromParam(value: string | undefined): StationAction {
  return value === "review" ? "review" : "attempt";
}
