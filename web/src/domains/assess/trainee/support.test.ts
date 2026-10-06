import assert from "node:assert/strict";
import test from "node:test";
import type { MySitting, MySlot, OrgStation } from "@/domains/assess/trainee/api";
import {
  continueLabel,
  greeting,
  greetingFor,
  firstName,
  liveSittings,
  orderedSlots,
  phaseLabel,
  practisable,
  progressOf,
  slotStatus,
  sortSittings,
  spotlight,
  stationsCompleted,
  summaryLine,
} from "@/domains/assess/trainee/support";

function slot(over: Partial<MySlot> & { id: string }): MySlot {
  return {
    slot_index: 0,
    status: "scheduled",
    started_at: null,
    ended_at: null,
    exam_completed_at: null,
    room_name: null,
    station_title: "Chest pain",
    is_active: false,
    joinable: false,
    ...over,
  } as MySlot;
}

function sitting(over: Partial<MySitting> = {}): MySitting {
  return {
    id: "s1",
    circuit_id: "c1",
    circuit_name: "Morning circuit",
    name: "Spring OSCE",
    mode: "exam",
    status: "scheduled",
    org_id: "o1",
    org_slug: "kings",
    scheduled_for: null,
    can_join: false,
    live: false,
    paused: false,
    slots: [],
    ...over,
  } as MySitting;
}

test("a completed station is completed however the status string reads", () => {
  assert.equal(slotStatus(slot({ id: "a", exam_completed_at: "2026-09-18T09:00:00" })).done, true);
  assert.equal(slotStatus(slot({ id: "b", status: "completed" })).done, true);
  assert.equal(slotStatus(slot({ id: "c", status: "in_progress" })).done, false);
  assert.equal(slotStatus(slot({ id: "d", status: "scheduled" })).label, "Not started");
});

test("a skipped station is finished, and says so rather than offering a way in", () => {
  const status = slotStatus(slot({ id: "a", status: "skipped" }));
  assert.equal(status.done, true);
  assert.equal(status.label, "Skipped");
});

test("slots are read in the order they will be sat", () => {
  const found = orderedSlots(
    sitting({
      slots: [slot({ id: "b", slot_index: 2 }), slot({ id: "a", slot_index: 0 })],
    }),
  );
  assert.deepEqual(
    found.map((each) => each.id),
    ["a", "b"],
  );
});

test("progress counts what is finished, not what has a room", () => {
  const found = progressOf(
    sitting({
      slots: [
        slot({ id: "a", status: "completed" }),
        slot({ id: "b", status: "in_progress", room_name: "r" }),
        slot({ id: "c" }),
      ],
    }),
  );
  assert.deepEqual(found, { completed: 1, total: 3 });
});

test("live sittings are the ones the backend says may be joined", () => {
  const open = sitting({ id: "open", can_join: true });
  const running = sitting({ id: "running", live: true, can_join: false });
  assert.deepEqual(
    liveSittings([open, running]).map((each) => each.id),
    ["open"],
  );
});

test("a live sitting outranks one scheduled sooner", () => {
  const later = sitting({ id: "live", live: true, scheduled_for: "2026-10-01T09:00:00Z" });
  const sooner = sitting({ id: "soon", scheduled_for: "2026-09-20T09:00:00Z" });
  const done = sitting({ id: "done", status: "completed" });
  assert.deepEqual(
    sortSittings([done, sooner, later]).map((each) => each.id),
    ["live", "soon", "done"],
  );
  assert.equal(spotlight([done, sooner, later])?.id, "live");
});

test("an unscheduled sitting sorts after a scheduled one of the same standing", () => {
  const dated = sitting({ id: "dated", scheduled_for: "2026-09-20T09:00:00Z" });
  const undated = sitting({ id: "undated", scheduled_for: null });
  assert.deepEqual(
    sortSittings([undated, dated]).map((each) => each.id),
    ["dated", "undated"],
  );
});

test("stations completed adds up across everything somebody is rostered onto", () => {
  const one = sitting({ slots: [slot({ id: "a", status: "completed" }), slot({ id: "b" })] });
  const two = sitting({ slots: [slot({ id: "c", exam_completed_at: "2026-09-18T09:00:00" })] });
  assert.equal(stationsCompleted([one, two]), 2);
});

test("the summary claims a station count only for an examination that has them", () => {
  assert.equal(
    summaryLine(sitting({ mode: "training", slots: [slot({ id: "a" })] })),
    "Practice circuit",
  );
  assert.equal(summaryLine(sitting({ slots: [] })), "Examination");
  assert.match(
    summaryLine(sitting({ slots: [slot({ id: "a", status: "completed" }), slot({ id: "b" })] })),
    /1 of 2 stations completed/,
  );
});

test("the spotlight label leads with the thing that needs doing now", () => {
  assert.equal(continueLabel(sitting({ can_join: true })), "Your station is open");
  assert.equal(continueLabel(sitting({ live: true, paused: true })), "Paused by your supervisor");
  assert.equal(
    continueLabel(sitting({ slots: [slot({ id: "a", status: "completed" })] })),
    "Finished",
  );
  assert.equal(continueLabel(sitting()), "Not started");
});

test("an unknown phase is shown in words rather than dropped", () => {
  assert.equal(phaseLabel("reading"), "Reading");
  assert.equal(phaseLabel("wrap_up"), "wrap up");
  assert.equal(phaseLabel(null), "Now");
});

test("only a published station with a version can be practised", () => {
  const stations = [
    { id: "a", title: "Bravo", status: "published", current_version_id: "v1" },
    { id: "b", title: "Alpha", status: "published", current_version_id: "v2" },
    { id: "c", title: "Draft", status: "draft", current_version_id: "v3" },
    { id: "d", title: "Unversioned", status: "published", current_version_id: null },
  ] as OrgStation[];
  assert.deepEqual(
    practisable(stations).map((each) => each.title),
    ["Alpha", "Bravo"],
  );
});

test("the greeting follows the clock, and a missing name is not a blank hello", () => {
  assert.equal(greeting(new Date(2026, 8, 19, 9)), "Good morning");
  assert.equal(greeting(new Date(2026, 8, 19, 14)), "Good afternoon");
  assert.equal(greeting(new Date(2026, 8, 19, 20)), "Good evening");
  assert.equal(firstName("  Amara Okafor "), "Amara");
  assert.equal(firstName("   "), null);
  assert.equal(firstName("tutor@ashford.ac.uk"), null);
  assert.equal(greetingFor("Amara Okafor", new Date(2026, 8, 19, 9)), "Good morning, Amara.");
  assert.equal(greetingFor(null, new Date(2026, 8, 19, 20)), "Good evening.");
});
