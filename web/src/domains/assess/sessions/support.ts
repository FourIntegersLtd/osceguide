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
    "The patient has not joined this station. Resend the patient if this does not clear.",
  attempt_failed:
    "This station's consultation failed. Resend the patient, or redo the station once it is safe to.",
  clock_overdue:
    "The clock has run past this phase and the circuit has not moved on by itself. Advance it by hand.",
};

export function alertCopy(code: string): string {
  return ALERT_COPY[code] ?? code.replace(/_/g, " ");
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

/* ------------------------------------------------------------------------
 * The stepper.
 *
 * The four steps a supervisor walks, as the retiring runner drew them, with
 * one difference: every state below is read from the circuit rather than from
 * whatever this browser last did. Two supervisors on the same circuit now see
 * the same step.
 * --------------------------------------------------------------------- */

export type StepState = "done" | "active" | "idle";

export interface RunnerStep {
  number: number;
  label: string;
  sublabel: string;
  state: StepState;
}

export function runnerSteps(data: CircuitConsole): RunnerStep[] {
  const circuit = data.circuit;
  const slots = orderedSlots(data);
  const started = circuit.started_at !== null;
  const ended = circuit.ended_at !== null;
  const active = slots.find((slot) => slot.id === circuit.active_slot_id) ?? null;
  const position = active ? slots.findIndex((slot) => slot.id === active.id) + 1 : 0;

  const onStation: StepState = !started ? "idle" : active ? (ended ? "done" : "active") : "done";
  const reading: StepState = !active
    ? "idle"
    : circuit.phase === "reading"
      ? "active"
      : circuit.phase === "simulation" || slotProgress(active) === "completed"
        ? "done"
        : "idle";
  const consultation: StepState = !active
    ? "idle"
    : circuit.phase === "simulation"
      ? "active"
      : slotProgress(active) === "completed"
        ? "done"
        : "idle";

  return [
    {
      number: 1,
      label: "Start the circuit",
      sublabel: ended ? "Ended" : started ? "Running" : "Opens the room for everybody",
      state: started ? "done" : "active",
    },
    {
      number: 2,
      label: "On station",
      sublabel: !started
        ? "After the circuit starts"
        : active
          ? `${personLabel(active)} · station ${position} of ${slots.length}`
          : ended
            ? `${slots.filter((each) => slotProgress(each) === "completed").length} of ${slots.length} stations sat`
            : circuit.phase === "break"
              ? "Between stations"
              : "Waiting for the next station",
      state: onStation,
    },
    {
      number: 3,
      label: "Reading time",
      sublabel: !active
        ? "Once somebody is on station"
        : circuit.phase === "reading"
          ? "The candidate is reading the brief"
          : reading === "done"
            ? "Done for this station"
            : "Not running",
      state: reading,
    },
    {
      number: 4,
      label: "Consultation",
      sublabel: !active
        ? "After reading time"
        : circuit.phase === "simulation"
          ? circuit.agent_dispatched
            ? `Patient is live · ${stationLabel(active)}`
            : "Waiting for the patient to join"
          : consultation === "done"
            ? "Finished"
            : "After reading time",
      state: consultation,
    },
  ];
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
    parts.push(total > 0 ? `Ended · ${completed} of ${total} stations sat` : "Ended");
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
  return progress === "in_consultation" || progress === "completed" || slot.has_review;
}

export const EDIT_BLOCK_COPY: Record<string, string> = {
  circuit_ended: "This circuit has finished, so its stations can no longer be changed.",
  consultation_in_progress:
    "Someone is taking a station right now. Changing the stations would delete that consultation.",
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
  return EDIT_BLOCK_COPY[code] ?? "This circuit cannot be restructured right now.";
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
