import { readTranscript, type Transcript } from "@/capabilities/feedback";
import { listMyAttempts, type AttemptHistoryItem } from "@/capabilities/attempt-runner";
import type { CursorPage } from "@/foundation/hooks";

export type RecentAttempt = AttemptHistoryItem;

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

export const TRANSCRIPT_PAGE_LIMIT = 100;

/**
 * One page of the attempts a person could have a transcript for.
 *
 * There is no "list my transcripts" endpoint and there should not be: a
 * transcript belongs to an attempt, so the attempt history *is* the list.
 * `transcribable_only` leaves out an attempt still in `created` — it never
 * reached the room — server-side, so this never offers a page that would only
 * ever say "nothing was transcribed". `search` matches the exam code and the
 * kind label in SQL, newest first; it does not reach the formatted date shown
 * in the table, since the backend never indexed that.
 *
 * This reads `/me/attempts` rather than `/me/dashboard`'s `recent_attempts` —
 * that list is capped at ten for the dashboard's own purposes, which meant an
 * eleventh consultation was unreachable from here no matter how the table was
 * searched.
 */
export function listTranscribableAttempts(
  params: { cursor?: string | null; limit?: number; search?: string } = {},
  signal?: AbortSignal,
): Promise<CursorPage<RecentAttempt>> {
  return listMyAttempts(
    {
      cursor: params.cursor,
      limit: params.limit ?? TRANSCRIPT_PAGE_LIMIT,
      search: params.search,
      transcribableOnly: true,
    },
    signal,
  );
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
