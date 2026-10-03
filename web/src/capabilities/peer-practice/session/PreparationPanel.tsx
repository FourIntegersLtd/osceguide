"use client";

import { PatientRoleplayScript } from "@/capabilities/debrief/PatientRoleplayScript";
import { StationBrief } from "@/capabilities/attempt-runner/material/StationBrief";
import { ManagementPlan } from "@/capabilities/attempt-runner/material/ManagementPlan";
import { sectionsFor } from "@/capabilities/attempt-runner/material/AudienceSections";
import type { PracticeSession } from "../api";

type Station = NonNullable<PracticeSession["station"]>;

/** Not in the retiring client, which rendered nothing; a missing station is a failure, not an empty page. */
const missing = <p className="p-4 text-osce-body text-b2c-text-muted">Station material could not be loaded. Please retry the session.</p>;

/** The patient's roleplay script, one tab per patient section of the template. */
function PatientScript({ station }: { station: Station }) {
  return <PatientRoleplayScript noBorder sections={station.sections ?? []} />;
}

/** The reading screen once both have joined: the brief or the script, full width. */
export function PreparationPanel({ session }: { session: PracticeSession }) {
  const station = session.station;
  return (
    <div className="h-full overflow-hidden">
      <div className="h-full w-full p-3 md:mx-auto md:max-w-6xl md:p-6">
        {!station ? missing : session.my_role === "patient" ? (
          <PatientScript station={station} />
        ) : (
          <div
            className="h-full w-full overflow-y-auto rounded-osce-lg border border-osce-border bg-osce-surface p-4 md:p-6"
          >
            <StationBrief embedded brief={{ sections: station.sections ?? [] }} />
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * The column beside the video. In the consultation it is the same brief or
 * script as the reading phase; in the debrief it is the model answer.
 */
export function ConsultationPanel({ session, debrief }: { session: PracticeSession; debrief: boolean }) {
  const station = session.station;
  if (debrief) {
    const sections = station?.sections ?? [];
    return (
      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-4">
        <div className="flex-shrink-0 rounded-osce-lg bg-b2c-surface-muted px-4 py-3">
          <p className="text-osce-body font-semibold text-osce-ink-900">Discuss the case together</p>
          <p className="mt-0.5 text-osce-meta text-b2c-text-muted">
            Use the model answer below. Talk through what went well, what you would do differently, and any questions.
          </p>
        </div>
        {station && sectionsFor(sections, "examiner").length > 0 ? (
          <ManagementPlan review={{ station_id: station.station_id, station_title: station.title, sections }} />
        ) : (
          <p className="text-b2c-text-muted">No management plan available for this station.</p>
        )}
      </div>
    );
  }
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
      {!station ? missing : session.my_role === "patient" ? (
        <div className="min-h-0 flex-1">
          <PatientScript station={station} />
        </div>
      ) : (
        <div className="min-h-0 w-full flex-1 py-4 md:p-4">
          <StationBrief embedded brief={{ sections: station.sections ?? [] }} />
        </div>
      )}
    </div>
  );
}
