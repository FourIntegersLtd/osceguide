"use client";

import Markdown from "react-markdown";
import { AsyncBoundary } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { readAttemptBrief, type AttemptBrief } from "@/capabilities/attempt-runner";
import { StationBrief } from "@/capabilities/attempt-runner/material/StationBrief";
import { listOrgStations, type MySlot, type OrgStation } from "@/domains/assess/trainee/api";
import { readingBrief } from "@/domains/assess/trainee/support";

/**
 * The reading brief for one slot, during the reading phase.
 *
 * Two sources, decided by whether the backend has created an attempt yet:
 *
 * - **Before dispatch** (`attempt_id` is null): the candidate reads the org
 *   station's `reading_brief` (or `candidate_brief` fallback). The org station
 *   list gives a trainee caller a candidate-scoped projection server-side, and
 *   `readingBrief()` picks the field to show. Matched by `station_id`.
 *
 * - **After dispatch** (`attempt_id` is populated): the candidate reads their
 *   own attempt brief via `GET /attempts/{id}/brief`, which is the entitlement-
 *   checked path. Rendered through `StationBrief` for the exam-specific layout.
 *
 * The supervisor console uses the same org station list but matches by
 * `station_version_id` and sees the full content — see `CircuitRunner`.
 */
export function SlotReadingBrief({
  slot,
  orgSlug,
}: {
  slot: MySlot;
  orgSlug: string | null;
}) {
  if (slot.attempt_id) {
    return <AttemptBriefView attemptId={slot.attempt_id} />;
  }

  if (!orgSlug) return null;

  return <OrgStationBriefView orgSlug={orgSlug} slot={slot} />;
}

/** After dispatch: the attempt's own brief, entitlement-checked. */
function AttemptBriefView({ attemptId }: { attemptId: string }) {
  const state = useAsync(
    (signal) => readAttemptBrief(attemptId, signal),
    [attemptId],
  );

  return (
    <AsyncBoundary state={state}>
      {(brief: AttemptBrief) => (
        <div className="rounded-lg border border-b2b-border bg-b2b-surface p-4 sm:p-5">
          <h3 className="text-osce-body font-semibold text-b2b-headline mb-3">
            Reading brief
          </h3>
          <StationBrief brief={brief} />
        </div>
      )}
    </AsyncBoundary>
  );
}

/**
 * Before dispatch: the org station's reading brief.
 *
 * Fetches the org's station list and matches the slot to a station. The
 * backend is adding `station_id` to `MySlot`; until then the match falls back
 * to `station_title`.
 */
function OrgStationBriefView({
  orgSlug,
  slot,
}: {
  orgSlug: string;
  slot: MySlot;
}) {
  const state = useAsync(
    (signal) => listOrgStations(orgSlug, signal),
    [orgSlug],
  );

  return (
    <AsyncBoundary state={state}>
      {(stations: OrgStation[]) => {
        const station = matchStation(stations, slot);
        if (!station) return null;

        const brief = readingBrief(station);
        if (!brief) return null;

        return (
          <div className="rounded-lg border border-b2b-border bg-b2b-surface p-4 sm:p-5">
            <h3 className="text-osce-body font-semibold text-b2b-headline mb-3">
              Reading brief
            </h3>
            <div className="max-w-3xl text-sm leading-6 text-ink">
              <Markdown>{brief}</Markdown>
            </div>
          </div>
        );
      }}
    </AsyncBoundary>
  );
}

/**
 * Match a slot to its station in the org list.
 *
 * `MySlot.station_id` makes the match exact. The title fallback stays only
 * for rows served by a backend that predates the field.
 */
function matchStation(stations: OrgStation[], slot: MySlot): OrgStation | null {
  if (slot.station_id) {
    return stations.find((s) => s.id === slot.station_id) ?? null;
  }
  if (slot.station_title) {
    return stations.find((s) => s.title === slot.station_title) ?? null;
  }
  return null;
}
