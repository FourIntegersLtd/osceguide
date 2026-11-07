"use client";

import { Alert, EmptyState, Spinner } from "@/foundation/ui";
import { assessMeta } from "@/foundation/ui/b2bTokens";
import { boardRow } from "@/foundation/ui/boardKit";
import { useAsync } from "@/foundation/hooks";
import { RailSection } from "@/domains/assess/sessions/RailSection";
import { listInterventions } from "@/domains/assess/sessions/api";

/** The override actions, as an examiner would write them in a report. */
const ACTION_LABEL: Record<string, string> = {
  advance: "Advanced to the next station",
  pause: "Paused",
  resume: "Resumed",
  extend_clock: "Time added",
  reset_clock: "Timer restarted",
  resend_patient: "Patient sent in again",
  redo_station: "Station repeated",
  jump_to: "Moved to another station",
  auto_advance: "Automatic next station changed",
  floor_changed: "Open floor switched",
  mic_changed: "A microphone was changed",
  room_closed: "Room closed",
};

/**
 * Everything a human did to this examination, and why.
 *
 * This is the half of the overrides that makes them defensible: an examination
 * that was paused for eleven minutes needs to be able to say it was the fire
 * alarm. The retiring runner recorded none of it — the clock lived in a
 * browser, so there was nothing to record it against.
 *
 * Loaded when it is opened. An examination in progress is not the moment to
 * spend a request on a log nobody has asked for.
 */
export function InterventionsLog({ orgSlug, circuitId }: { orgSlug: string; circuitId: string }) {
  return (
    <RailSection id="changes" title="Changes made during the circuit" lazy>
      <Entries orgSlug={orgSlug} circuitId={circuitId} />
    </RailSection>
  );
}

function Entries({ orgSlug, circuitId }: { orgSlug: string; circuitId: string }) {
  const log = useAsync(
    (signal) => listInterventions(orgSlug, circuitId, signal),
    [orgSlug, circuitId],
  );

  if (log.loading) return <Spinner />;
  if (log.error) {
    return <Alert tone="danger">Could not load the changes. Reload the page and try again.</Alert>;
  }

  const items = log.data?.items ?? [];
  if (items.length === 0) {
    return <EmptyState title="No changes were made." />;
  }

  return (
    <ol className="m-0 list-none p-0">
      {items.map((entry) => (
        <li key={entry.id} className={`${boardRow} px-0`}>
          <span className="min-w-0 flex-[1_1_240px]">
            {ACTION_LABEL[entry.action] ?? entry.action.replace(/_/g, " ")}
            <span className={`block ${assessMeta}`}>
              {`${new Date(entry.at).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })} · ${entry.reason ?? "No reason given."}`}
            </span>
          </span>
        </li>
      ))}
    </ol>
  );
}
