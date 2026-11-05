import assert from "node:assert/strict";
import test from "node:test";
import type { CircuitConsole, ConsoleSlot } from "@/domains/assess/sessions/api";
import {
  pickFrame,
  validOverrideSeconds,
  alertCopy,
  observerSubtitle,
  orderedSlots,
  runnerSteps,
  markable,
  slotProgress,
  summariseCircuit,
} from "@/domains/assess/sessions/support";

function slot(over: Partial<ConsoleSlot> & { id: string; slot_index: number }): ConsoleSlot {
  return {
    status: "scheduled",
    room_name: null,
    started_at: null,
    ended_at: null,
    exam_completed_at: null,
    trainee: { user_id: "u-a", name: "Person a", email: null, trainee_id: null },
    station: { version_id: `v-${over.id}`, station_id: null, title: `Station ${over.id}`, version: 1, status: "published" },
    has_review: false,
    marked: false,
    draft_reviews: 0,
    is_active: false,
    attempt_id: null,
    phase: null,
    phase_started_at: null,
    phase_ends_at: null,
    ...over,
  } as ConsoleSlot;
}

function console_(over: {
  mode?: string;
  circuit?: Partial<CircuitConsole["circuit"]>;
  slots?: ConsoleSlot[];
}): CircuitConsole {
  return {
    sitting: {
      id: "s1",
      name: "June sitting",
      mode: over.mode ?? "training",
      sitting_type: "group_training",
      status: "in_progress",
      scheduled_for: null,
      rubric_version_id: "rv",
    },
    circuit: {
      id: "c1",
      name: "Circuit A",
      timing: { reading_minutes: 2, simulation_minutes: 10, break_minutes: 0, breaks: [] },
      active_slot_id: null,
      room_name: null,
      started_at: null,
      ended_at: null,
      agent_dispatched: false,
      supervisor: null,
      phase: null,
      phase_started_at: null,
      phase_ends_at: null,
      phase_seq: 0,
      paused: false,
      paused_at: null,
      auto_advance: true,
      elapsed_seconds: null,
      remaining_seconds: null,
      alerts: [],
      editable: true,
      edit_block: null,
      ...over.circuit,
    },
    slots: over.slots ?? [],
  } as CircuitConsole;
}

test("slots are drawn in the order they are sat, not the order they arrived", () => {
  const data = console_({ slots: [slot({ id: "b", slot_index: 2 }), slot({ id: "a", slot_index: 0 })] });
  assert.deepEqual(
    orderedSlots(data).map((each) => each.id),
    ["a", "b"],
  );
});

test("an alert code is shown as a sentence, never as the code", () => {
  assert.match(alertCopy("no_running_attempt"), /patient has not joined/i);
  // An unknown code is still readable rather than raw.
  assert.equal(alertCopy("some_new_code"), "some new code");
  // The console is already in the room, so it says what to do there.
  assert.equal(
    alertCopy("voice_fault", "console"),
    "Voice fault in the room. The candidate may not hear the patient.",
  );
  assert.equal(
    alertCopy("attempt_failed", "console"),
    "This station's attempt failed. Resend the patient or redo the station.",
  );
  assert.equal(alertCopy("clock_overdue", "console"), "The clock is overdue. Move the circuit on by hand.");
  assert.equal(alertCopy("clock_overdue", "console", null, 40), "The clock is overdue by 40 s. Move the circuit on by hand.");
  assert.equal(alertCopy("clock_overdue", "board", null, 95), "The clock is overdue by 1 min 35 s. Advance it by hand.");
});

test("a station the circuit skipped is not a completed one", () => {
  assert.equal(slotProgress(slot({ id: "a", slot_index: 0, status: "skipped" })), "skipped");
  assert.equal(slotProgress(slot({ id: "a", slot_index: 0, status: "completed" })), "completed");
  assert.equal(slotProgress(slot({ id: "a", slot_index: 0, status: "scheduled" })), "waiting");
});

test("before it starts, the only live step is starting it", () => {
  const steps = runnerSteps(console_({ slots: [slot({ id: "a", slot_index: 0 })] }));
  assert.deepEqual(
    steps.map((step) => step.state),
    ["active", "idle", "idle", "idle"],
  );
});

test("during reading, the consultation step has not happened yet", () => {
  const data = console_({
    circuit: { started_at: "2026-09-19T09:00:00Z", active_slot_id: "a", phase: "reading" },
    slots: [slot({ id: "a", slot_index: 0, status: "reading" })],
  });
  const steps = runnerSteps(data);
  assert.deepEqual(
    steps.map((step) => step.state),
    ["done", "active", "active", "idle"],
  );
});

test("a dispatched patient is named on the consultation step", () => {
  const data = console_({
    circuit: {
      started_at: "2026-09-19T09:00:00Z",
      active_slot_id: "a",
      phase: "simulation",
      agent_dispatched: true,
    },
    slots: [slot({ id: "a", slot_index: 0, status: "in_consultation" })],
  });
  const steps = runnerSteps(data);
  assert.deepEqual(
    steps.map((step) => step.state),
    ["done", "active", "done", "active"],
  );
  assert.match(steps[3]?.sublabel ?? "", /Patient is live/);
});

test("the header says which station of how many, and that it is paused", () => {
  const data = console_({
    mode: "exam",
    circuit: {
      started_at: "2026-09-19T09:00:00Z",
      active_slot_id: "b",
      phase: "simulation",
      paused: true,
    },
    slots: [
      slot({ id: "a", slot_index: 0, status: "completed" }),
      slot({ id: "b", slot_index: 1 }),
      slot({ id: "c", slot_index: 2 }),
    ],
  });
  assert.equal(observerSubtitle(data), "Person a · Station 2 of 3 · Consultation · Paused");
});

test("an ended circuit says how much of it was actually sat", () => {
  const data = console_({
    circuit: { started_at: "2026-09-19T09:00:00Z", ended_at: "2026-09-19T10:00:00Z" },
    slots: [
      slot({ id: "a", slot_index: 0, status: "completed" }),
      slot({ id: "b", slot_index: 1, status: "skipped" }),
    ],
  });
  assert.equal(observerSubtitle(data), "Person a · Ended · 1 of 2 stations sat");
});

test("a circuit ended with nothing sat does not claim every station was", () => {
  const data = console_({
    circuit: { started_at: "2026-09-19T09:00:00Z", ended_at: "2026-09-19T09:05:00Z" },
    slots: [
      slot({ id: "a", slot_index: 0, status: "skipped" }),
      slot({ id: "b", slot_index: 1, status: "skipped" }),
    ],
  });
  assert.equal(runnerSteps(data)[1]?.sublabel, "0 of 2 stations sat");
});

test("a station is markable from its consultation, not its reading time", () => {
  const of = (status: string, marked = false) => slot({ id: "a", slot_index: 0, status, marked });
  assert.equal(markable(of("scheduled")), false);
  assert.equal(markable(of("reading")), false);
  assert.equal(markable(of("skipped")), false);
  assert.equal(markable(of("in_consultation")), true);
  assert.equal(markable(of("completed")), true);
  assert.equal(markable(of("reading", true)), true);
});

test("a circuit of two trainees counts them instead of naming the first", () => {
  const second = { user_id: "u-b", name: "Person b", email: null, trainee_id: null };
  const data = console_({
    slots: [slot({ id: "a", slot_index: 0 }), slot({ id: "b", slot_index: 1, trainee: second })],
  });
  assert.equal(observerSubtitle(data), "Not started · 2 trainees");
  assert.equal(observerSubtitle(console_({ slots: [slot({ id: "a", slot_index: 0 })] })), "Person a · Not started");
});

test("a frame fetched after an action wins until the stream pushes a newer one", () => {
  assert.equal(pickFrame("pushed-1", { frame: "fetched", over: "pushed-1" }, "first"), "fetched");
  assert.equal(pickFrame("pushed-2", { frame: "fetched", over: "pushed-1" }, "first"), "pushed-2");
  assert.equal(pickFrame(null, null, "first"), "first");
  assert.equal(pickFrame(null, { frame: "fetched", over: null }, "first"), "fetched");
});

test("an override's seconds must be a whole number the server accepts", () => {
  assert.equal(validOverrideSeconds(60), true);
  assert.equal(validOverrideSeconds(0), false);
  assert.equal(validOverrideSeconds(Number.NaN), false);
  assert.equal(validOverrideSeconds(3601), false);
  assert.equal(validOverrideSeconds(1.5), false);
});

test("summariseCircuit counts candidates and who is still to review", () => {
  const data = console_({
    slots: [
      slot({ id: "a", slot_index: 0, status: "completed", marked: true }),
      slot({ id: "b", slot_index: 1, status: "completed", trainee: { user_id: "u-b", name: "B", email: null, trainee_id: null } }),
      slot({ id: "c", slot_index: 2, status: "scheduled", trainee: { user_id: "u-c", name: "C", email: null, trainee_id: null } }),
    ],
  });
  const summary = summariseCircuit(data, { state: "draft" });
  assert.equal(summary.candidates, 2);
  assert.equal(summary.toReview, 1);
  assert.equal(summary.unmarked.length, 1);
  assert.equal(summary.readyToPublish, false);
});

test("summariseCircuit adds up the drafts waiting to be completed", () => {
  const data = console_({
    slots: [
      slot({ id: "a", slot_index: 0, status: "completed", draft_reviews: 1 }),
      slot({ id: "b", slot_index: 1, status: "completed", draft_reviews: 1, trainee: { user_id: "u-b", name: "B", email: null, trainee_id: null } }),
    ],
  });
  assert.equal(summariseCircuit(data, null).drafts, 2);
  assert.equal(summariseCircuit(console_({ slots: [slot({ id: "a", slot_index: 0 })] }), null).drafts, 0);
});

test("summariseCircuit: all marked is ready to publish only when the review is read and unpublished", () => {
  const data = console_({ slots: [slot({ id: "a", slot_index: 0, status: "completed", marked: true })] });
  assert.equal(summariseCircuit(data, { state: "draft" }).readyToPublish, true);
  assert.equal(summariseCircuit(data, { state: "published" }).readyToPublish, false);
  assert.equal(summariseCircuit(data, null).readyToPublish, false);
});
