import assert from "node:assert/strict";
import test from "node:test";
import type { CircuitConsole, ConsoleSlot } from "@/domains/assess/sessions/api";
import {
  alertCopy,
  observerSubtitle,
  orderedSlots,
  runnerSteps,
  slotProgress,
} from "@/domains/assess/sessions/support";

function slot(over: Partial<ConsoleSlot> & { id: string; slot_index: number }): ConsoleSlot {
  return {
    status: "scheduled",
    room_name: null,
    started_at: null,
    ended_at: null,
    exam_completed_at: null,
    trainee: { user_id: `u-${over.id}`, name: `Person ${over.id}`, email: null, trainee_id: null },
    station: { version_id: `v-${over.id}`, station_id: null, title: `Station ${over.id}`, version: 1, status: "published" },
    has_review: false,
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
