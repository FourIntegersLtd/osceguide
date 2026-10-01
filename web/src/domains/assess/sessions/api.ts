import { hasCode, platformRequest, type components } from "@/foundation/platform-client";
import type { RoomGrant } from "@/foundation/livekit";
import { orgPath } from "@/domains/assess/api";

export type CircuitConsole = components["schemas"]["CircuitConsole"];
export type ConsoleSlot = components["schemas"]["ConsoleSlot"];
export type ConsoleCircuit = components["schemas"]["ConsoleCircuit"];
export type Circuit = components["schemas"]["CircuitRead"];
export type Intervention = components["schemas"]["Intervention"];
export type DispatchResult = components["schemas"]["DispatchResult"];
export type EditLock = components["schemas"]["EditLock"];

const circuit = (slug: string, circuitId: string) =>
  `${orgPath(slug)}/circuits/${encodeURIComponent(circuitId)}`;

export function readConsole(
  slug: string,
  circuitId: string,
  signal?: AbortSignal,
): Promise<CircuitConsole> {
  return platformRequest<CircuitConsole>(`${circuit(slug, circuitId)}/console`, { signal });
}

/** A station version as the staff running it read it: every audience's sections, empty when untemplated. */
export function readStaffSections(
  slug: string,
  versionId: string,
  signal?: AbortSignal,
): Promise<StaffSection[]> {
  return platformRequest<StaffSection[]>(
    `${orgPath(slug)}/station-versions/${encodeURIComponent(versionId)}/sections`,
    { signal },
  );
}

export type StaffSection = components["schemas"]["AudienceSectionRead"];

export function consoleStreamPath(slug: string, circuitId: string): string {
  return `${circuit(slug, circuitId)}/console/stream`;
}

/* ------------------------------------------------------------------------
 * The supervisor's controls.
 *
 * Every one of these is a server-side transition on the circuit, not a local
 * edit that is later saved. The retiring console kept the clock in the
 * supervisor's browser and broadcast it over LiveKit data packets, so a
 * refresh lost the examination's timing and two supervisors disagreed about
 * it.
 *
 * Everything below `start` carries a `reason`. The backend writes it to the
 * interventions record beside the action, which is what makes "the clock was
 * extended" answerable with "because the fire alarm went" months later. The
 * field is optional there and asked for here: an examination that cannot say
 * why it was interrupted is not a defensible one.
 * --------------------------------------------------------------------- */

/** The run itself: no reason, because starting and advancing are the exam. */
export const runControls = {
  start: (slug: string, circuitId: string) => post<Circuit>(slug, circuitId, "start"),
  advance: (slug: string, circuitId: string) => post<Circuit>(slug, circuitId, "advance"),
  end: (slug: string, circuitId: string) => post<Circuit>(slug, circuitId, "end"),
};

/** The overrides: a human stepping in, and saying why. */
export const overrides = {
  pause: (slug: string, circuitId: string, reason: string | null) =>
    post<Circuit>(slug, circuitId, "pause", { reason }),
  resume: (slug: string, circuitId: string, reason: string | null) =>
    post<Circuit>(slug, circuitId, "resume", { reason }),
  resetClock: (slug: string, circuitId: string, reason: string | null) =>
    post<Circuit>(slug, circuitId, "reset-clock", { reason }),
  extendClock: (slug: string, circuitId: string, seconds: number, reason: string | null) =>
    post<Circuit>(slug, circuitId, "extend-clock", { seconds, reason }),
  resendPatient: (slug: string, circuitId: string, reason: string | null) =>
    post<DispatchResult>(slug, circuitId, "resend-patient", { reason }),
  redoStation: (slug: string, circuitId: string, slotId: string, reason: string | null) =>
    post<Circuit>(slug, circuitId, "redo-station", { slot_id: slotId, reason }),
  jumpTo: (slug: string, circuitId: string, slotId: string, reason: string | null) =>
    post<Circuit>(slug, circuitId, "jump-to", { slot_id: slotId, reason }),
};

/**
 * Whether the circuit drives its own clock.
 *
 * Off, the circuit waits on the supervisor at each station boundary. It is a
 * PATCH rather than an override because it changes how the examination runs
 * from here, rather than correcting something that happened.
 */
export function setAutoAdvance(
  slug: string,
  circuitId: string,
  enabled: boolean,
): Promise<Circuit> {
  return platformRequest<Circuit>(`${circuit(slug, circuitId)}/auto-advance`, {
    method: "PATCH",
    body: { enabled },
  });
}

/** Everything a human did to this examination, and why. */
export function listInterventions(
  slug: string,
  circuitId: string,
  signal?: AbortSignal,
): Promise<components["schemas"]["Interventions"]> {
  return platformRequest<components["schemas"]["Interventions"]>(
    `${circuit(slug, circuitId)}/interventions`,
    { signal },
  );
}

/**
 * Late arrivals, and where they go.
 *
 * Appended to the end of the circuit, never inserted. `stationVersionIds` is
 * positional against `traineeIds` — the nth arrival takes the nth station —
 * exactly as circuit creation pairs them. Omit it and everybody joins the
 * station the circuit is already running, which is what a single latecomer to a
 * group practice wants and is the default the dialog offers.
 *
 * The refusals this can now answer, all of them shown rather than retried:
 * `trainee_already_on_circuit` (409) — they are already on it, and the slots
 * did not change; `station_not_on_circuit` (409) — a station nobody here is
 * sitting is not where a latecomer belongs, because naming one would change
 * what the circuit is; `invalid_circuit` (409) — the two lists did not line up;
 * `not_permitted_in_mode` (409) — an examination is one candidate by
 * construction, and appending is refused there by design.
 */
export function appendTrainees(
  slug: string,
  circuitId: string,
  traineeIds: string[],
  stationVersionIds?: string[],
): Promise<Circuit> {
  return platformRequest<Circuit>(`${circuit(slug, circuitId)}/append-trainees`, {
    method: "POST",
    body: {
      trainee_ids: traineeIds,
      // Absent means "the active station", so an empty list is not sent as an
      // empty list — that would be the short-list case the server refuses.
      ...(stationVersionIds && stationVersionIds.length > 0
        ? { station_version_ids: stationVersionIds }
        : {}),
    },
  });
}

/**
 * Publish one summary across everything marked on this circuit.
 *
 * The retiring runner called this "Publish circuit feedback" and the backend
 * calls it finalising the circuit's review. Same act: the per-station reviews
 * stop being drafts and the candidates can read them.
 */
export function finalizeCircuitReview(
  slug: string,
  circuitId: string,
  mergedNotes: string | null,
): Promise<components["schemas"]["CircuitReviewRead"]> {
  return platformRequest<components["schemas"]["CircuitReviewRead"]>(
    `${circuit(slug, circuitId)}/review/finalize`,
    { method: "POST", body: { merged_notes: mergedNotes } },
  );
}

export type CircuitReview = components["schemas"]["CircuitReviewRead"];

/**
 * Whether this circuit's feedback has been published, as the server has it.
 *
 * `GET …/review` is the read beside `…/review/finalize`, answering the same
 * `CircuitReviewRead`; `review_not_found` means nothing has been published.
 */
export type CircuitReviewState =
  | { state: "published"; review: CircuitReview }
  | { state: "unpublished"; review: CircuitReview | null };

export async function readCircuitReview(
  slug: string,
  circuitId: string,
  signal?: AbortSignal,
): Promise<CircuitReviewState> {
  try {
    const review = await platformRequest<CircuitReview>(`${circuit(slug, circuitId)}/review`, {
      signal,
    });
    return review.finalized_at ? { state: "published", review } : { state: "unpublished", review };
  } catch (error) {
    if (hasCode(error, "review_not_found")) return { state: "unpublished", review: null };
    throw error;
  }
}

/** A room-admin token, so an examiner can listen in without being heard. */
export function observerToken(
  slug: string,
  circuitId: string,
  signal?: AbortSignal,
): Promise<RoomGrant> {
  return platformRequest<RoomGrant>(`${circuit(slug, circuitId)}/observer-token`, {
    method: "POST",
    signal,
  });
}

function post<T>(
  slug: string,
  circuitId: string,
  action: string,
  body?: Record<string, unknown>,
): Promise<T> {
  return platformRequest<T>(`${circuit(slug, circuitId)}/${action}`, {
    method: "POST",
    body: body ?? {},
  });
}
