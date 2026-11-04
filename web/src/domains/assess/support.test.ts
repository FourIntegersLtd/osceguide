import assert from "node:assert/strict";
import test from "node:test";
import type { Programme, Sitting, SittingMode } from "@/domains/assess/api";
import type { SittingFormValues } from "@/domains/assess/support";
import {
  moveItem,
  toggleInSet,
  circuitLeads,
  fieldDateTime,
  hasChanges,
  programmeChoices,
  sittingChanges,
  sittingEditLock,
  sittingRunning,
  sittingsEmptyDescription,
  sittingFilterQuery,
  NO_SITTING_FILTERS,
  sittingsScopeNote,
} from "@/domains/assess/support";

/** The smallest thing `sittingEditLock` can be asked about. */
function sitting(circuits: { started_at: string | null }[]): Pick<Sitting, "circuits"> {
  return { circuits: circuits as Sitting["circuits"] };
}

function full(over: Partial<Sitting> = {}): Sitting {
  return {
    id: "s1",
    name: "March mock",
    mode: "training",
    status: "scheduled",
    sitting_type: "group_training",
    programme_id: "p1",
    rubric_version_id: "r1",
    scheduled_for: null,
    circuits: [],
    ...over,
  } as Sitting;
}

test("a sitting with nothing on it can still be composed", () => {
  const lock = sittingEditLock(sitting([]));
  assert.equal(lock.modeFrozen, false);
  assert.equal(lock.assessmentFrozen, false);
});

test("circuits freeze the mode before they freeze the marking", () => {
  const lock = sittingEditLock(sitting([{ started_at: null }]));
  assert.equal(lock.circuits, 1);
  assert.equal(lock.begun, false);
  assert.equal(lock.modeFrozen, true, "the mode composes the slots, so it is chosen before they exist");
  assert.equal(lock.assessmentFrozen, false, "nothing has been examined yet");
});

test("a started circuit freezes every assessment-bearing field", () => {
  assert.equal(sittingEditLock(sitting([{ started_at: "2026-03-01T09:00:00Z" }])).assessmentFrozen, true);
});

test("a circuit that has finished still counts as begun", () => {
  // `ended_at` is not the question the server asks: an examination that is over
  // is the one whose marks must keep meaning what they meant.
  const lock = sittingEditLock(sitting([{ started_at: "2026-03-01T09:00:00Z" }]));
  assert.equal(lock.begun, true);
  assert.equal(lock.assessmentFrozen, true);
});

test("restating the sitting is not a change", () => {
  const before = full({ scheduled_for: "2026-03-01T09:00:00Z" });
  assert.deepEqual(
    sittingChanges(before, {
      name: before.name,
      mode: "training",
      programmeId: "p1",
      cohortId: "",
      scheduledFor: fieldDateTime(before.scheduled_for),
    }),
    {},
  );
  assert.equal(hasChanges(sittingChanges(before, { ...form(before) })), false);
});

test("only what differs is sent, and a rename alone stays open on a begun sitting", () => {
  const before = full({ scheduled_for: "2026-03-01T09:00:00Z", mode: "exam" });
  const changes = sittingChanges(before, {
    name: "  March mock OSCE  ",
    mode: "exam",
    programmeId: "p1",
    cohortId: "",
    scheduledFor: fieldDateTime(before.scheduled_for),
  });
  assert.deepEqual(changes, { name: "March mock OSCE" });
});

test("a mode change carries the sitting type with it", () => {
  const changes = sittingChanges(full(), {
    name: "March mock",
    mode: "exam",
    programmeId: "p1",
    cohortId: "",
    scheduledFor: "",
  });
  assert.deepEqual(changes, { mode: "exam", sittingType: "examination" });
});

test("the same appointment in the other spelling is not a change", () => {
  const date = new Date(2026, 2, 1, 9, 0);
  const before = full({ scheduled_for: date.toISOString() });
  const changes = sittingChanges(before, {
    name: "March mock",
    mode: "training",
    programmeId: "p1",
    cohortId: "",
    scheduledFor: fieldDateTime(before.scheduled_for),
  });
  assert.equal(changes.scheduledFor, undefined);
});

test("an emptied date is a request to unschedule, not an absent field", () => {
  const before = full({ scheduled_for: new Date(2026, 2, 1, 9, 0).toISOString() });
  const changes = sittingChanges(before, {
    name: "March mock",
    mode: "training",
    programmeId: "p1",
    cohortId: "",
    scheduledFor: "",
  });
  assert.deepEqual(changes, { scheduledFor: null });
  assert.equal(hasChanges(changes), true);
});

test("a programme is only sent when it moves, and never as an empty pick", () => {
  const changes = sittingChanges(full(), {
    name: "March mock",
    mode: "training",
    programmeId: "",
    cohortId: "",
    scheduledFor: "",
  });
  assert.equal(changes.programmeId, undefined);
});

test("the picker keeps the programme a sitting is already on, retired or not", () => {
  const items = [
    { id: "p1", exam_name: "One", exam_code: "A", status: "retired" },
    { id: "p2", exam_name: "Two", exam_code: "B", status: "active" },
    { id: "p3", exam_name: "Three", exam_code: "C", status: "retired" },
  ];
  assert.deepEqual(
    programmeChoices(items as Programme[], "p1").map((programme) => programme.id),
    ["p1", "p2"],
  );
});

test("an unparseable date reads as unscheduled rather than as Invalid Date", () => {
  assert.equal(fieldDateTime("not a date"), "");
  assert.equal(fieldDateTime(null), "");
});

function form(
  sitting: Pick<Sitting, "name" | "mode" | "programme_id" | "scheduled_for" | "cohort_id">,
): SittingFormValues {
  const mode: SittingMode = sitting.mode === "exam" ? "exam" : "training";
  return {
    name: sitting.name,
    mode,
    programmeId: sitting.programme_id ?? "",
    cohortId: sitting.cohort_id ?? "",
    scheduledFor: fieldDateTime(sitting.scheduled_for),
  };
}

// R-21: the sitting page's badge read only "live" as running, and the backend writes in_progress.
test("a sitting the backend marks in_progress is running", () => {
  assert.equal(sittingRunning("in_progress"), true);
  assert.equal(sittingRunning("scheduled"), false);
  assert.equal(sittingRunning("completed"), false);
});

test("only people who can run a circuit are offered as its lead", () => {
  const staff = [
    { user_id: "a", role: "owner" },
    { user_id: "b", role: "supervisor" },
    { user_id: "c", role: "trainee" },
    { user_id: "d", role: "practice_user" },
  ];
  assert.deepEqual(circuitLeads(staff).map((member) => member.user_id), ["a", "b"]);
});

test("the sittings list says when its filters cover only what has loaded", () => {
  assert.equal(sittingsScopeNote(25, false), null);
  assert.equal(
    sittingsScopeNote(25, true),
    "Next up covers the 25 sittings loaded so far. Load more to include the rest.",
  );
});

test("only somebody who can schedule is told to schedule", () => {
  assert.equal(sittingsEmptyDescription(true), "Schedule your first one to get started.");
  assert.equal(sittingsEmptyDescription(false), "An administrator schedules sittings; they will appear here.");
});

test("toggleInSet adds a missing id, removes a present one and leaves the original alone", () => {
  const original = new Set(["a"]);
  assert.deepEqual([...toggleInSet(original, "b")], ["a", "b"]);
  assert.deepEqual([...toggleInSet(original, "a")], []);
  assert.deepEqual([...original], ["a"]);
});

test("holding a sitting for a cohort, moving it and clearing it are changes; restating is not", () => {
  const unheld = full();
  assert.deepEqual(sittingChanges(unheld, { ...form(unheld), cohortId: "c1" }), { cohortId: "c1" });
  const held = full({ cohort_id: "c1" });
  assert.deepEqual(sittingChanges(held, form(held)), {});
  assert.deepEqual(sittingChanges(held, { ...form(held), cohortId: "c2" }), { cohortId: "c2" });
  assert.deepEqual(sittingChanges(held, { ...form(held), cohortId: "" }), { cohortId: null });
});

test("only the filters that are set go to the server", () => {
  assert.deepEqual(sittingFilterQuery(NO_SITTING_FILTERS), {});
  assert.deepEqual(
    sittingFilterQuery({
      status: "completed",
      mode: "exam",
      search: " may ",
      programmeId: "p1",
      from: "2026-05-01",
      to: "2026-05-31",
    }),
    {
      status: "completed",
      mode: "exam",
      search: "may",
      programme_id: "p1",
      scheduled_from: "2026-05-01",
      scheduled_to: "2026-05-31",
    },
  );
  assert.deepEqual(sittingFilterQuery({ ...NO_SITTING_FILTERS, search: "   " }), {});
});

test("moveItem swaps an item with its neighbour above or below", () => {
  assert.deepEqual(moveItem(["a", "b", "c"], 1, -1), ["b", "a", "c"]);
  assert.deepEqual(moveItem(["a", "b", "c"], 1, 1), ["a", "c", "b"]);
});

test("moveItem leaves the order alone at either end", () => {
  assert.deepEqual(moveItem(["a", "b", "c"], 0, -1), ["a", "b", "c"]);
  assert.deepEqual(moveItem(["a", "b", "c"], 2, 1), ["a", "b", "c"]);
});

test("moveItem does not change its input", () => {
  const input = ["a", "b", "c"];
  const out = moveItem(input, 0, 1);
  assert.deepEqual(input, ["a", "b", "c"]);
  assert.notEqual(out, input);
});
