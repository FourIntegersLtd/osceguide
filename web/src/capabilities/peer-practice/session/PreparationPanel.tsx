"use client";

import { PatientRoleplayScript } from "@/capabilities/debrief/PatientRoleplayScript";
import { StationBrief } from "@/capabilities/attempt-runner/material/StationBrief";
import { ManagementPlan } from "@/capabilities/attempt-runner/material/ManagementPlan";
import { b2cCard } from "@/foundation/ui/productTokens";
import type { PracticeSession } from "../api";

type Station = NonNullable<PracticeSession["station"]>;

/** Not in the retiring client, which rendered nothing; a missing station is a failure, not an empty page. */
const missing = <p className="p-4 text-osce-body text-b2c-text-muted">Station material could not be loaded. Please retry the session.</p>;

/** The doctor's candidate brief, in the exam's own layout. */
function DoctorReading({ session, station }: { session: PracticeSession; station: Station }) {
  if (station.doctor_information || station.scenario) {
    return (
      <StationBrief
        embedded
        brief={{ exam_code: session.exam_code, doctor_information: station.doctor_information, scenario: station.scenario }}
      />
    );
  }
  return <p className="whitespace-pre-wrap px-4 text-osce-body text-osce-ink-900">{station.reading_brief ?? ""}</p>;
}

/** The patient's roleplay script: History, ICE & Concerns and Persona tabs. */
function PatientScript({ station }: { station: Station }) {
  return (
    <PatientRoleplayScript
      noBorder
      stationData={{ patient_information: station.patient_information ?? { expanded_history: station.patient_script ?? undefined } }}
    />
  );
}

/** The reading screen once both have joined: the brief or the script, full width. */
export function PreparationPanel({ session }: { session: PracticeSession }) {
  const station = session.station;
  return (
    <div className="h-full overflow-hidden bg-b2c-surface-muted/50">
      <div className="h-full w-full md:mx-auto md:max-w-6xl md:p-6">
        {!station ? missing : session.my_role === "patient" ? (
          <PatientScript station={station} />
        ) : (
          <div
            className={`h-full w-full overflow-y-auto rounded-none border-x-0 px-0 py-4 md:rounded-2xl md:border-x md:p-6 ${b2cCard}`}
          >
            <DoctorReading session={session} station={station} />
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * The column beside the video. In the consultation it is the same brief or
 * script as the reading phase; in the debrief it is the management plan.
 */
export function ConsultationPanel({ session, debrief }: { session: PracticeSession; debrief: boolean }) {
  const station = session.station;
  if (debrief) {
    const hasPlan = Boolean(station?.management || station?.management_plan);
    return (
      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-4">
        <div className="flex-shrink-0 rounded-lg border border-osce-accent-subtle bg-osce-accent-muted px-4 py-3 text-osce-body text-osce-ink-900">
          <p className="font-medium">Discuss the case and share insights</p>
          <p className="mt-1 text-osce-accent-hover/90">
            Use the management plan below. Talk through what went well, what you’d do differently, and any questions.
          </p>
        </div>
        {station && hasPlan ? (
          <ManagementPlan
            review={{
              exam_code: session.exam_code,
              station_id: station.station_id,
              station_title: station.title,
              patient_information: station.patient_information,
              management_plan: station.management,
              scenario: station.scenario,
              teaching: station.teaching,
            }}
          />
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
          <DoctorReading session={session} station={station} />
        </div>
      )}
    </div>
  );
}
