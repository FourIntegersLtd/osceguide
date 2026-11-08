"use client";

import Markdown from "react-markdown";
import { AsyncBoundary } from "@/foundation/ui";
import { boardCard, boardRow } from "@/foundation/ui/boardKit";
import { useAsync } from "@/foundation/hooks";
import { AudienceSections } from "@/capabilities/attempt-runner";
import { listOrgStations, type OrgStation } from "@/domains/assess/trainee/api";
import { readCandidateSections, type CircuitConsole, type StaffSection } from "@/domains/assess/sessions/api";
import { cardTitle, foldBody, foldSummary } from "@/domains/assess/chrome";
import { candidateSections, untemplatedBrief } from "@/domains/assess/sessions/supervisorBrief";

/**
 * The station the supervisor console is running, as its staff read it.
 *
 * Only the candidate's (doctor's) brief is shown, never the patient's script,
 * hidden material, the examiner's notes or the faculty's. A templated station
 * is read by its candidate sections; a station bound to no template falls back
 * to its reading brief from the org station list, matched by `station_version_id`.
 *
 * Shown when the circuit has an active slot, so the supervisor can see what
 * the candidate is reading while the station runs.
 */
export function SupervisorReadingBrief({
  data,
  orgSlug,
}: {
  data: CircuitConsole;
  orgSlug: string;
}) {
  const activeSlotId = data.circuit.active_slot_id;
  const activeSlot = (data.slots ?? []).find((s) => s.id === activeSlotId);
  if (!activeSlot) return null;

  const versionId = activeSlot.station.version_id;
  if (!versionId) return null;

  return (
    <SupervisorBrief orgSlug={orgSlug} versionId={versionId} title={activeSlot.station.title} />
  );
}

function SupervisorBrief({
  orgSlug,
  versionId,
  title,
}: {
  orgSlug: string;
  versionId: string;
  title?: string | null;
}) {
  const state = useAsync((signal) => readCandidateSections(orgSlug, versionId, signal), [orgSlug, versionId]);
  return (
    <AsyncBoundary state={state}>
      {(all: StaffSection[]) => {
        const sections = candidateSections(all);
        return sections.length > 0 ? (
          <section className={boardCard} data-board="station-content">
            <div className={`${boardRow} border-t-0`}>
              <h2 className={cardTitle}>Station content{title ? `: ${title}` : ""}</h2>
            </div>
            <AudienceSections sections={sections} variant="brief" />
          </section>
        ) : (
          <UntemplatedBrief orgSlug={orgSlug} versionId={versionId} title={title} />
        );
      }}
    </AsyncBoundary>
  );
}

/** An untemplated station's string fields, the only shape it has. */
function UntemplatedBrief({
  orgSlug,
  versionId,
  title,
}: {
  orgSlug: string;
  versionId: string;
  title?: string | null;
}) {
  const state = useAsync(
    (signal) => listOrgStations(orgSlug, signal),
    [orgSlug],
  );

  return (
    <AsyncBoundary state={state}>
      {(stations: OrgStation[]) => {
        const station = stations.find((s) => s.current_version_id === versionId);
        if (!station?.content) return null;

        const readingBrief = untemplatedBrief(station.content);

        return (
          <section className={boardCard} data-board="station-content">
            <div className={`${boardRow} border-t-0`}>
              <h2 className={cardTitle}>Station content{title ? `: ${title}` : ""}</h2>
            </div>
            {readingBrief ? (
              <details className="group">
                <summary className={foldSummary}>What the candidate reads</summary>
                <div className={foldBody}>
                  <Markdown>{readingBrief}</Markdown>
                </div>
              </details>
            ) : null}
            {!readingBrief ? (
              <p className={`${boardRow} text-osce-ink-500`}>Nothing to show for this station.</p>
            ) : null}
          </section>
        );
      }}
    </AsyncBoundary>
  );
}
