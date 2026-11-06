"use client";

import Markdown from "react-markdown";
import { AsyncBoundary } from "@/foundation/ui";
import { boardCard, boardRow } from "@/foundation/ui/boardKit";
import { useAsync } from "@/foundation/hooks";
import { AudienceSections } from "@/capabilities/attempt-runner";
import { listOrgStations, type OrgStation } from "@/domains/assess/trainee/api";
import { readStaffSections, type CircuitConsole, type StaffSection } from "@/domains/assess/sessions/api";
import { cardTitle, foldBody, foldSummary } from "@/domains/assess/chrome";

/**
 * The station the supervisor console is running, as its staff read it.
 *
 * A templated station is read by its template's sections: the candidate's
 * brief, the patient's script, the examiner's notes and the faculty's own
 * material (set-up, faculty script, debrief), each block drawn by its type. A
 * station bound to no template has no sections, and falls back to its string
 * fields from the org station list, matched by `station_version_id`.
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
  const state = useAsync((signal) => readStaffSections(orgSlug, versionId, signal), [orgSlug, versionId]);
  return (
    <AsyncBoundary state={state}>
      {(sections: StaffSection[]) =>
        sections.length > 0 ? (
          <section className={boardCard} data-board="station-content">
            <div className={`${boardRow} border-t-0`}>
              <h2 className={cardTitle}>Station content{title ? `: ${title}` : ""}</h2>
            </div>
            <AudienceSections sections={sections} variant="collapsible" />
          </section>
        ) : (
          <UntemplatedBrief orgSlug={orgSlug} versionId={versionId} title={title} />
        )
      }
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

        const content = station.content;
        const readingBrief = extractReadingBrief(content);
        const fullContent = extractFullContent(content);

        return (
          <section className={boardCard} data-board="station-content">
            <div className={`${boardRow} border-t-0`}>
              <h2 className={cardTitle}>Station content{title ? `: ${title}` : ""}</h2>
            </div>
            {readingBrief ? (
              <details className="group">
                <summary className={foldSummary}>Reading brief</summary>
                <div className={foldBody}>
                  <Markdown>{readingBrief}</Markdown>
                </div>
              </details>
            ) : null}
            {fullContent ? (
              <details className="group">
                <summary className={foldSummary}>Full content</summary>
                <div className={foldBody}>
                  <Markdown>{fullContent}</Markdown>
                </div>
              </details>
            ) : null}
            {!readingBrief && !fullContent ? (
              <p className={`${boardRow} text-osce-ink-500`}>No content available for this station.</p>
            ) : null}
          </section>
        );
      }}
    </AsyncBoundary>
  );
}

/**
 * Extract the reading brief from station content: `reading_brief`, else the
 * older `candidate_brief` (the server's `stations.domain_content.BRIEF_KEYS`).
 */
function extractReadingBrief(content: Record<string, unknown>): string | null {
  for (const key of ["reading_brief", "candidate_brief"]) {
    const value = content[key];
    if (typeof value === "string" && value.trim()) return value;
  }
  return null;
}

/**
 * Extract the full content as markdown.
 *
 * The supervisor sees everything — patient information, marking guidance, and
 * the candidate brief. Rendered as a single markdown document by concatenating
 * the string fields.
 */
function extractFullContent(content: Record<string, unknown>): string | null {
  const parts: string[] = [];
  for (const [key, value] of Object.entries(content)) {
    if (key === "reading_brief" || key === "candidate_brief") continue;
    if (typeof value === "string" && value.trim()) {
      parts.push(`### ${key.replace(/_/g, " ")}\n\n${value}`);
    }
  }
  return parts.length > 0 ? parts.join("\n\n---\n\n") : null;
}
