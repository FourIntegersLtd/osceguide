import { readTranscript, type Transcript } from "@/capabilities/feedback";
import { listMyAttempts, type AttemptHistoryItem } from "@/capabilities/attempt-runner";
import type { CursorPage } from "@/foundation/hooks";

export type RecentAttempt = AttemptHistoryItem;

export type { Transcript };
export { readTranscript };

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
