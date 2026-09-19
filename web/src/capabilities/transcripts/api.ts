import { platformRequest, type components } from "@/foundation/platform-client";
import { readTranscript, type Transcript } from "@/capabilities/feedback";

export type RecentAttempt = components["schemas"]["RecentAttempt"];
type Dashboard = components["schemas"]["Dashboard"];

export type { Transcript };
export { readTranscript };

/**
 * How the product spells the reasons an attempt happened.
 *
 * The backend's `attempts.Kind`, which is one table and one vocabulary for
 * what the retiring clients called a practice, a mock station, a debrief and
 * an exam slot. An unknown kind shows its own word rather than nothing, so a
 * kind added on the server is readable here before anybody edits this file.
 */
const KIND_LABELS: Record<string, string> = {
  practice: "Practice",
  set_station: "Mock station",
  debrief: "Debrief",
  self_practice: "Self practice",
  exam_slot: "Exam station",
  peer: "Peer session",
};

export function kindLabel(kind: string): string {
  return KIND_LABELS[kind] ?? kind.replace(/_/g, " ");
}

/**
 * The attempts a person could have a transcript for.
 *
 * There is no "list my transcripts" endpoint and there should not be: a
 * transcript belongs to an attempt, so the attempt history *is* the list. An
 * attempt still in `created` never reached the room, so it is left out rather
 * than offered as a page that would only ever say "nothing was transcribed".
 */
export async function listTranscribableAttempts(signal?: AbortSignal): Promise<RecentAttempt[]> {
  const dashboard = await platformRequest<Dashboard>("/api/v1/me/dashboard", { signal });
  return (dashboard.recent_attempts ?? [])
    .filter((attempt) => attempt.status !== "created")
    .sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at));
}

/**
 * API timestamps, in the product's format.
 *
 * Naive ISO strings from the backend are UTC — Python's `utcnow().isoformat()`
 * — and reading them as local time shifted every date in the retiring client
 * by an hour each summer.
 */
export function formatAttemptDate(iso: string | null | undefined): string {
  if (!iso) return "No date provided";
  const normalised =
    /[zZ]$/.test(iso) || /[+-]\d{2}:?\d{2}$/.test(iso) || !iso.includes("T") ? iso : `${iso}Z`;
  const date = new Date(normalised);
  if (!Number.isFinite(date.getTime())) return "Invalid date";
  return date.toLocaleDateString("en-GB", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
