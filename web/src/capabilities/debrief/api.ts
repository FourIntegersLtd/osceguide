import { isPlatformError, platformRequest, type components } from "@/foundation/platform-client";
import type { StartedAttemptRef } from "@/capabilities/attempt-runner";
import type { RoomGrant } from "@/foundation/livekit";
import type { AssistantSurface } from "@/capabilities/surface";

export type DebriefSummary = components["schemas"]["DebriefSummaryRead"];
export type AthenaDoctorSession = components["schemas"]["SessionRead"];
export type PatientRoleplay = components["schemas"]["PatientRoleplayRead"];

export function readPatientRoleplay(attemptId: string, signal?: AbortSignal): Promise<PatientRoleplay> {
  return platformRequest(`/api/v1/attempts/${encodeURIComponent(attemptId)}/roleplay`, { signal });
}

export function startAttemptDebrief(attemptId: string): Promise<StartedAttemptRef> {
  return platformRequest(`/api/v1/attempts/${encodeURIComponent(attemptId)}/debriefs`, { method: "POST" });
}
type StartedAttempt = components["schemas"]["StartedAttempt"];

export interface AthenaDoctorClientContext {
  surface: AssistantSurface;
  route: string;
}

export interface AthenaDoctorStationContext {
  attemptId: string;
  examCode: string;
  stationId?: string | null;
  stationTitle?: string | null;
  patientName?: string | null;
  patientGender?: string | null;
  patientBiodata?: string | null;
  doctorRole?: string | null;
  doctorTask?: string | null;
  clinicalScenario?: string | null;
  backgroundOverview?: string | null;
  patientInformation?: string[];
  ice?: string[];
  managementPoints?: string[];
  stationVersionId?: string | null;
}

/**
 * Talking an attempt through with the tutor.
 *
 * Its own route on the backend rather than a flag on "start attempt", because
 * it is a different act with a different limit and a different refusal: a
 * debrief is *about* a station already sat, and `nothing_to_debrief` is what
 * comes back for asking to discuss one that was not.
 *
 * Nothing had ever called this — the retiring client ran its debrief through a
 * separate voice service with no attempt behind it, which is why a debrief
 * left no trace on the attempt history. Here it is an attempt like any other,
 * so the runner, the room token and the worker contract are all the shared
 * ones.
 */
export async function startDebrief(
  setId: string,
  entryId: string,
  signal?: AbortSignal,
): Promise<StartedAttemptRef> {
  const started = await platformRequest<StartedAttempt>(
    `/api/v1/me/station-sets/${encodeURIComponent(setId)}/entries/${encodeURIComponent(entryId)}/debriefs`,
    { method: "POST", signal, idempotencyKey: `debrief:${setId}:${entryId}` },
  );
  return { id: started.attempt_id };
}

export function startAthenaDoctorSession(
  station: AthenaDoctorStationContext,
  client: AthenaDoctorClientContext,
  signal?: AbortSignal,
): Promise<AthenaDoctorSession> {
  return platformRequest<AthenaDoctorSession>("/api/v1/assistant/sessions", {
    method: "POST",
    body: {
      session_type: "athena-doctor",
      // The backend rebuilds the doctor's prompt from this station version; without it the doctor
      // runs on a one-line generic prompt and answers like a help assistant.
      station_version_id: station.stationVersionId ?? null,
      extras: {
        client,
        station: {
          attempt_id: station.attemptId,
          exam_code: station.examCode,
          station_id: station.stationId ?? null,
          station_name: station.stationTitle ?? null,
          station_title: station.stationTitle ?? null,
          station_patient_name: station.patientName ?? null,
          station_patient_gender: station.patientGender ?? null,
          station_patient_biodata: station.patientBiodata ?? null,
          doctor_role: station.doctorRole ?? null,
          doctor_task: station.doctorTask ?? null,
          clinical_scenario: station.clinicalScenario ?? null,
          background_overview: station.backgroundOverview ?? null,
          patient_information: station.patientInformation ?? [],
          ice: station.ice ?? [],
          management_points: station.managementPoints ?? [],
          app_type: station.examCode,
        },
      },
    },
    signal,
  });
}

export function athenaDoctorVoiceToken(sessionId: string, signal?: AbortSignal): Promise<RoomGrant> {
  return platformRequest<RoomGrant>(
    `/api/v1/assistant/sessions/${encodeURIComponent(sessionId)}/voice-token`,
    { method: "POST", signal },
  );
}

export interface DebriefPage {
  items: DebriefSummary[];
  next_cursor?: string | null;
}

/**
 * A page of past debriefs, filtered by the server.
 *
 * `attemptId`, `stationVersionId` and `setEntryId` narrow to one source
 * consultation, one station's history, or one set entry's — each summary
 * names its source consultation, and the server does that matching in SQL
 * rather than the caller walking its whole history and filtering in the
 * browser.
 */
export function listDebriefs(
  params: {
    attemptId?: string | null;
    stationVersionId?: string | null;
    setEntryId?: string | null;
    cursor?: string | null;
    limit?: number;
  } = {},
  signal?: AbortSignal,
): Promise<DebriefPage> {
  return platformRequest<DebriefPage>("/api/v1/me/debriefs", {
    signal,
    query: {
      attempt_id: params.attemptId ?? undefined,
      station_version_id: params.stationVersionId ?? undefined,
      set_entry_id: params.setEntryId ?? undefined,
      cursor: params.cursor ?? undefined,
      limit: params.limit,
    },
  });
}

/** One summary, read directly rather than found by walking the whole history. */
export async function readDebrief(
  id: string,
  signal?: AbortSignal,
): Promise<DebriefSummary | null> {
  try {
    return await platformRequest<DebriefSummary>(
      `/api/v1/me/debriefs/${encodeURIComponent(id)}`,
      { signal },
    );
  } catch (error) {
    if (isPlatformError(error) && error.status === 404) return null;
    throw error;
  }
}

/** The insights and the plan are open JSON on the wire; a reader narrows them. */
export function asLines(value: unknown[]): string[] {
  return value.flatMap((item) => {
    if (typeof item === "string") return item.trim() ? [item] : [];
    const text = (item as { text?: unknown })?.text;
    return typeof text === "string" && text.trim() ? [text] : [];
  });
}

/** API timestamps are UTC even when they carry no zone. */
export function debriefDate(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const normalised =
    /[zZ]$/.test(iso) || /[+-]\d{2}:?\d{2}$/.test(iso) || !iso.includes("T") ? iso : `${iso}Z`;
  const date = new Date(normalised);
  return Number.isFinite(date.getTime()) ? date : null;
}
