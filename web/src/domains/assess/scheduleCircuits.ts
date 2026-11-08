import { createCircuit, createExamCircuits, timingBody } from "@/domains/assess/api";
import {
  circuitPlan,
  circuitTiming,
  eachCircuitJobs,
  startOffsetFor,
  stationAssessorsFor,
  type ScheduleDraft,
} from "@/domains/assess/scheduleSitting";

/**
 * Make the circuits of a sitting that already exists.
 *
 * The wizard calls it once; if it fails the sitting is real and the person lands
 * on it, where "Try again" calls it with `already` set to how many circuits were
 * made, so nothing is made twice and nobody is skipped.
 */
export async function createSittingCircuits(
  orgSlug: string,
  sittingId: string,
  draft: ScheduleDraft,
  already: number,
): Promise<void> {
  const plan = circuitPlan(draft);
  const stationVersionIds = draft.stations.map((station) => station.version_id);
  const timing = circuitTiming(draft);
  const stationAssessors = stationAssessorsFor(draft);
  if (plan.kind === "training") {
    await createCircuit(orgSlug, sittingId, {
      name: draft.name.trim(),
      stationVersionIds,
      traineeIds: draft.candidateIds,
      supervisorUserId: draft.supervisorId || null,
      timing,
    });
  } else if (plan.kind === "bulk") {
    await createExamCircuits(orgSlug, sittingId, {
      name_prefix: "Exam",
      candidate_user_ids: draft.candidateIds,
      station_version_ids: stationVersionIds,
      supervisor_user_id: draft.supervisorId || null,
      start_offset_minutes: 0,
      timing: timingBody(timing),
      station_assessors: stationAssessors,
    });
  } else {
    for (const job of eachCircuitJobs(plan.candidateIds, already)) {
      try {
        await createCircuit(orgSlug, sittingId, {
          name: `Exam ${job.number}`,
          stationVersionIds,
          traineeIds: [job.candidate],
          supervisorUserId: (draft.perCandidate ? draft.supervisorByCandidate[job.candidate] : draft.supervisorId) || null,
          timing,
          startOffsetMinutes: startOffsetFor(draft, job.number - 1),
          stationAssessors,
        });
      } catch (cause) {
        // Circuits before this one exist now: a retry carries on from here.
        throw Object.assign(cause instanceof Error ? cause : new Error(String(cause)), { created: job.number - 1 });
      }
    }
  }
}

/** The circuits made in all when it failed; `before` when the failure was not part-way through the list. */
export function circuitsMade(cause: unknown, before = 0): number {
  return (cause as { created?: number }).created ?? before;
}

/** A sitting whose circuits did not all get made: its frozen answers, and where to carry on. */
export interface PendingCircuits {
  draft: ScheduleDraft;
  created: number;
  message: string;
}

const key = (sittingId: string) => `pending-circuits:${sittingId}`;

/**
 * Kept in the tab's session so the sitting page can offer "Try again" with the
 * answers the wizard had: a snapshot, so changing the wizard afterwards cannot
 * make a retry build something other than what was reviewed.
 */
export function savePending(sittingId: string, pending: PendingCircuits, store: Pick<Storage, "setItem"> = sessionStorage): void {
  try {
    store.setItem(key(sittingId), JSON.stringify(pending));
  } catch {
    // Storage blocked: the sitting page still opens, just without the retry.
  }
}

export function loadPending(sittingId: string, store: Pick<Storage, "getItem"> = sessionStorage): PendingCircuits | null {
  try {
    const raw = store.getItem(key(sittingId));
    return raw ? (JSON.parse(raw) as PendingCircuits) : null;
  } catch {
    return null;
  }
}

export function clearPending(sittingId: string, store: Pick<Storage, "removeItem"> = sessionStorage): void {
  try {
    store.removeItem(key(sittingId));
  } catch {
    // Nothing to clear.
  }
}
