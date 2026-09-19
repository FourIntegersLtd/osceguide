import { platformRequest, type components } from "@/foundation/platform-client";
import type { StartedAttemptRef } from "@/capabilities/attempt-runner";

export type DebriefSummary = components["schemas"]["DebriefSummaryRead"];
type TutorMemory = components["schemas"]["TutorMemoryRead"];
type StartedAttempt = components["schemas"]["StartedAttempt"];

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

/**
 * What past debriefs concluded.
 *
 * Read off the tutor's memory, which is where the summariser writes them: one
 * row per debriefed attempt, holding the narrative, the insights and what was
 * agreed. There is no debriefs collection to list and no debrief to read by
 * id — see `docs/port-gaps.md`.
 */
export async function listDebriefs(signal?: AbortSignal): Promise<DebriefSummary[]> {
  const memory = await platformRequest<TutorMemory>("/api/v1/me/tutor-memory", { signal });
  return [...(memory.debrief_summaries ?? [])].sort(
    (a, b) => Date.parse(b.created_at) - Date.parse(a.created_at),
  );
}

/** One debrief, found in the list the tutor's memory returns. */
export async function readDebrief(
  id: string,
  signal?: AbortSignal,
): Promise<DebriefSummary | null> {
  const debriefs = await listDebriefs(signal);
  return debriefs.find((debrief) => debrief.id === id) ?? null;
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
