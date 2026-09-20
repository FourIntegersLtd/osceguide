"use client";

import { PatientRoleplayScript } from "@/capabilities/debrief/PatientRoleplayScript";
import { StationBrief } from "@/capabilities/attempt-runner/material/StationBrief";
import { ManagementPlan } from "@/capabilities/attempt-runner/material/ManagementPlan";
import { Alert, ModalCallout } from "@/foundation/ui";
import type { PracticeSession } from "../api";

export function PreparationPanel({ session, debrief = false }: { session: PracticeSession; debrief?: boolean }) {
  const station = session.station;
  if (!station) return <Alert tone="warning">Station material could not be loaded. Please retry the session.</Alert>;
  if (debrief) return <div className="space-y-4">
    <ModalCallout><strong>Debrief</strong><br />Discuss what went well and what could be improved. Use the management plan to guide your feedback.</ModalCallout>
    <ManagementPlan review={{ exam_code: session.exam_code, station_id: station.station_id,
      station_title: station.title, patient_information: station.patient_information,
      management_plan: station.management, scenario: station.scenario, teaching: station.teaching }} />
  </div>;
  if (session.my_role === "patient") return <PatientRoleplayScript stationData={{ patient_information: station.patient_information ?? { expanded_history: station.patient_script } }} />;
  if (station.doctor_information || station.scenario) return <StationBrief embedded brief={{
    exam_code: session.exam_code, doctor_information: station.doctor_information, scenario: station.scenario,
  }} />;
  return <div className="rounded-panel border border-border bg-surface p-6">
    <h2 className="mb-4 font-semibold">{station.title}</h2>
    <p className="whitespace-pre-wrap">{station.reading_brief || "The station brief is unavailable. Please retry the session."}</p>
  </div>;
}
