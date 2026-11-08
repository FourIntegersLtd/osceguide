import type { CircuitConsole, ConsoleSlot } from "@/domains/assess/sessions/api";

/**
 * Everything the runner derives from one console frame.
 *
 * Pure, and in its own file, because these are the judgements that decide what
 * a supervisor is told in an examination hall — whether the patient is late,
 * whose station is running, whether a control is safe to press. The retiring
 * runner made each of them inline in a layout component, differently in the
 * training and exam trees, and neither could be tested.
 */

/** The circuit's phases, as the backend spells them. */
export type RunPhase = "reading" | "simulation" | "break";

export const PHASE_LABEL: Record<string, string> = {
  reading: "Reading time",
  simulation: "Consultation",
  break: "Break",
};

export function phaseLabel(phase: string | null | undefined): string {
  if (!phase) return "Not running";
  return PHASE_LABEL[phase] ?? phase;
}

/**
 * The alerts, in English.
 *
 * The backend raises stable codes on purpose — "the board decides how to say
 * it" — and the rebuilt console printed the code itself, so a supervisor read
 * `no_running_attempt` off the screen mid-examination.
 */
export const ALERT_COPY: Record<string, string> = {
  no_running_attempt:
    "The patient has not joined this station yet. Wait a few seconds, then choose Resend the patient.",
  attempt_failed:
    "The consultation stopped. Choose Resend the patient. If it fails again, redo the station when the candidate is ready.",
  voice_fault:
    "The voice link is down, so candidates may not hear the patient. It will retry. If it is still down after a minute, choose Resend the patient.",
  clock_overdue:
    "Time is up for this part but the circuit did not move on. Choose Next station to move it on yourself.",
};

/** The same alerts as the supervisor sees them in the room, where "do this" matters more than why. */
const CONSOLE_ALERT_COPY: Record<string, string> = {
  attempt_failed: "The consultation stopped working. Choose Resend the patient. If that fails, redo the station.",
  voice_fault: "Voice problem. The candidate may not hear the patient. Choose Resend the patient. Tell the candidate if it continues.",
  clock_overdue: "Time is up for this part. Choose Next station to move the circuit on.",
};

/**
 * The alert in words. `station` is the station's number when the room is on one
 * (a formal exam: one candidate, so a slot's place is the station's number); the
 * api's alert is a code with no station of its own.
 */
export function alertCopy(
  code: string,
  where: "board" | "console" = "board",
  station?: number | null,
  overdueSeconds?: number | null,
): string {
  if (code === "clock_overdue" && overdueSeconds) {
    const late = overdueSeconds >= 60 ? `${Math.floor(overdueSeconds / 60)} min ${overdueSeconds % 60} s` : `${overdueSeconds} s`;
    return `Time ran out ${late} ago and the circuit has not moved on. ${where === "console" ? "Choose Next station to move the circuit on." : "Choose Next station to move it on yourself."}`;
  }
  if (station) {
    if (code === "attempt_failed") return `Station ${station} stopped working. Choose Resend the patient. If that fails, redo the station.`;
    if (code === "no_running_attempt") return `The patient has not joined Station ${station} yet. Wait a few seconds, then choose Resend the patient.`;
  }
  if (where === "console" && CONSOLE_ALERT_COPY[code]) return CONSOLE_ALERT_COPY[code];
  return ALERT_COPY[code] ?? code.replace(/_/g, " ");
}

/** The station a formal exam's room is on, counted from one; null for a training rotation or when none is running. */
export function examStationNumber(mode: string, slotIndex: number | null | undefined): number | null {
  return mode === "exam" && typeof slotIndex === "number" ? slotIndex + 1 : null;
}

/** A person's name, then their email, then something rather than nothing. */
export function personLabel(slot: ConsoleSlot): string {
  return slot.trainee.name ?? slot.trainee.email ?? "Candidate";
}

export function stationLabel(slot: ConsoleSlot): string {
  return slot.station.title ?? "Station";
}

/** Slots in the order they are sat, whatever order they arrived in. */
export function orderedSlots(data: CircuitConsole): ConsoleSlot[] {
  return (data.slots ?? []).slice().sort((a, b) => a.slot_index - b.slot_index);
}

/** A station a supervisor sat and has not marked. */
export type UnmarkedStation = { slotId: string; attemptId: string | null };

/** The review page of a slot, with its attempt when it has one. */
export const slotReviewPath = (station: UnmarkedStation): string =>
  `/slots/${station.slotId}/review${station.attemptId ? `?attempt=${station.attemptId}` : ""}`;

export type SlotProgress = "waiting" | "reading" | "in_consultation" | "completed" | "skipped";

export function slotProgress(slot: ConsoleSlot): SlotProgress {
  if (slot.status === "completed" || slot.exam_completed_at) return "completed";
  if (slot.status === "skipped") return "skipped";
  if (slot.status === "reading") return "reading";
  if (slot.status === "in_consultation") return "in_consultation";
  return "waiting";
}

export const PROGRESS_LABEL: Record<SlotProgress, string> = {
  waiting: "Not started",
  reading: "Reading",
  in_consultation: "In consultation",
  completed: "Completed",
  skipped: "Skipped",
};

export function progressTone(progress: SlotProgress): "success" | "warning" | "danger" | "neutral" {
  if (progress === "completed") return "success";
  if (progress === "skipped") return "danger";
  if (progress === "waiting") return "neutral";
  return "warning";
}

/**
 * The line under an examiner's page title.
 *
 * An observer is not running anything, so the header answers the only two
 * questions they have: whose examination this is, and how far through it is.
 */
export function observerSubtitle(data: CircuitConsole): string {
  const slots = orderedSlots(data);
  const circuit = data.circuit;
  const trainees = new Set(slots.map((slot) => slot.trainee.user_id));
  // One trainee is named; more than one is counted, since naming only the
  // first would read as if the circuit were theirs alone.
  const candidate = trainees.size === 1 && slots[0] ? personLabel(slots[0]) : null;
  const total = slots.length;
  const completed = slots.filter((slot) => slotProgress(slot) === "completed").length;
  const parts: string[] = [];
  if (candidate) parts.push(candidate);
  const crowd = trainees.size > 1 ? `${trainees.size} trainees` : null;

  if (circuit.ended_at) {
    parts.push(total > 0 ? `Ended · ${completed} of ${total} stations done` : "Ended");
    if (crowd) parts.push(crowd);
    return parts.join(" · ");
  }
  if (!circuit.started_at) {
    parts.push("Not started");
    if (crowd) parts.push(crowd);
    return parts.join(" · ");
  }

  const active = slots.find((slot) => slot.id === circuit.active_slot_id) ?? null;
  if (active) {
    const position = slots.findIndex((slot) => slot.id === active.id) + 1;
    parts.push(`Station ${position} of ${total}`);
    parts.push(phaseLabel(circuit.phase));
  } else {
    parts.push(circuit.phase === "break" ? "Between stations" : "Running");
  }
  if (circuit.paused) parts.push("Paused");
  if (crowd) parts.push(crowd);
  return parts.join(" · ");
}

/**
 * A station may be marked once its consultation has started, or when it
 * already has a review. Reading time is not a consultation: a rubric filled in
 * then is for a candidate who has not spoken yet.
 */
export function markable(slot: ConsoleSlot): boolean {
  const progress = slotProgress(slot);
  return progress === "in_consultation" || progress === "completed" || slot.marked;
}

export const EDIT_BLOCK_COPY: Record<string, string> = {
  circuit_ended: "This circuit has finished, so its stations can no longer be changed.",
  consultation_in_progress:
    "Someone is taking a station right now. Changing the stations would lose their recording. Wait until they finish.",
  feedback_recorded:
    "Feedback has already been given on these stations, so they cannot be changed.",
};

/**
 * Why a circuit's slots cannot be restructured, in the reader's language.
 *
 * The backend sends a code precisely so that this file — not a `catch` on an
 * English sentence — decides what a supervisor reads. A circuit that may be
 * edited answers with no block at all, and the edit screen leaves the form alone.
 */
export function editLockNotice(circuit: {
  editable?: boolean;
  edit_block?: string | null;
}): string | null {
  if (circuit.editable !== false && !circuit.edit_block) return null;
  const code = circuit.edit_block ?? "";
  return EDIT_BLOCK_COPY[code] ?? "You cannot change this circuit's stations right now. Reload the page. If it is still locked, the circuit has already started.";
}

/**
 * The frame to draw. A frame fetched right after an action beats the stream's older one,
 * until the stream pushes something newer (`over` is the stream frame it was fetched over).
 */
export function pickFrame<T>(
  stream: T | null,
  fetched: { frame: T; over: T | null } | null,
  initial: T | null,
): T | null {
  if (fetched && fetched.over === stream) return fetched.frame;
  return stream ?? initial;
}

export const MAX_EXTEND_SECONDS = 3600;

/** `extend-clock` takes 1-3600 whole seconds. */
export function validOverrideSeconds(seconds: number): boolean {
  return Number.isInteger(seconds) && seconds >= 1 && seconds <= MAX_EXTEND_SECONDS;
}

/** Stations sat and not yet marked, in the order they are sat. */
export function unmarkedStations(data: CircuitConsole): (UnmarkedStation & { title: string; position: number })[] {
  return orderedSlots(data)
    .filter((slot) => !slot.marked && markable(slot))
    .map((slot) => ({
      slotId: slot.id,
      attemptId: slot.attempt_id ?? null,
      title: stationLabel(slot),
      position: slot.slot_index + 1,
    }));
}

/** One ended circuit as a supervisor's "still to review" prompt. */
export type CircuitSummary = {
  /** Candidates who sat a markable station. */
  candidates: number;
  /** Of those, candidates with a station still unmarked. */
  toReview: number;
  unmarked: ReturnType<typeof unmarkedStations>;
  /** Reviews started on this circuit's stations and not yet completed. */
  drafts: number;
  /** Every sat station is marked and the circuit's feedback is known not to be published. */
  readyToPublish: boolean;
};

/**
 * Pure summary of a circuit's console and its feedback review. `review` is null when that read
 * failed: unknown is never "ready to publish".
 */
export function summariseCircuit(data: CircuitConsole, review: { state: string } | null): CircuitSummary {
  const sat = orderedSlots(data).filter((slot) => markable(slot));
  const unmarked = unmarkedStations(data);
  return {
    candidates: new Set(sat.map((slot) => slot.trainee.user_id)).size,
    toReview: new Set(sat.filter((slot) => !slot.marked).map((slot) => slot.trainee.user_id)).size,
    unmarked,
    drafts: sat.reduce((total, slot) => total + slot.draft_reviews, 0),
    readyToPublish: unmarked.length === 0 && sat.length > 0 && review !== null && review.state !== "published",
  };
}
