import assert from "node:assert/strict";
import { describe, it } from "node:test";
import type { StationSet } from "@/domains/train/api";
import {
  anyStationMarking,
  attemptedVersionIds,
  attemptsWithTranscript,
  checkMilestone,
  chooseStations,
  groupSets,
  incompleteVersionIds,
  sessionAction,
  sessionMinutes,
  sessionState,
  stationFeedbackState,
  type AttemptStatusRecord,
} from "@/domains/train/mocks/model";

function set(over: Partial<StationSet> = {}): StationSet {
  return {
    id: "s1",
    name: "Session 1",
    exam_code: "sca",
    locked: false,
    completed_at: null,
    attempted_entries: 0,
    total_entries: 0,
    feedback_ready: false,
    entries: [],
    ...over,
  };
}

function entry(versionId: string, attempts: number, position = 0) {
  return {
    id: `e-${versionId}`,
    position,
    station_version_id: versionId,
    attempts,
    debrief_attempts: 0,
    feedback_ready: false,
    last_attempt_at: null,
  };
}

describe("sessionMinutes", () => {
  it("multiplies the exam's own clock by the station count", () => {
    assert.equal(sessionMinutes(3, { readingSeconds: 120, simulationSeconds: 600 }), 36);
  });

  it("is zero while the exam is still loading, rather than guessing", () => {
    assert.equal(sessionMinutes(3, null), 0);
  });
});

describe("sessionState / sessionAction", () => {
  it("reads locked ahead of everything else", () => {
    const lapsed = set({ locked: true, completed_at: "2026-01-01T00:00:00Z" });
    assert.equal(sessionState(lapsed), "locked");
    assert.equal(sessionAction(lapsed), "Review");
  });

  it("keeps an attempted-but-unfinished session on Start", () => {
    const partial = set({ attempted_entries: 1, total_entries: 3 });
    assert.equal(sessionState(partial), "attempted");
    assert.equal(sessionAction(partial), "Start");
  });

  it("keeps a finished session on Start until a station has been marked", () => {
    const done = set({ attempted_entries: 3, total_entries: 3, completed_at: "2026-01-01T00:00:00Z" });
    assert.equal(sessionState(done), "completed");
    assert.equal(sessionAction(done), "Start");
  });

  it("turns a session over to Review once feedback is ready", () => {
    const marked = set({ attempted_entries: 1, total_entries: 3, feedback_ready: true });
    assert.equal(sessionState(marked), "attempted");
    assert.equal(sessionAction(marked), "Review");
  });
});

describe("groupSets", () => {
  it("separates the current subscription from lapsed ones", () => {
    const grouped = groupSets([set({ id: "a" }), set({ id: "b", locked: true })]);
    assert.deepEqual(
      grouped.currentSubscription.map((item) => item.id),
      ["a"],
    );
    assert.deepEqual(
      grouped.inactiveSubscriptions.map((item) => item.id),
      ["b"],
    );
  });
});

describe("attempted and incomplete stations", () => {
  const sets = [
    set({ id: "a", entries: [entry("v1", 3), entry("v2", 1, 1)] }),
    set({ id: "b", entries: [entry("v3", 0), entry("v1", 2, 1)] }),
  ];

  it("collects every version with an attempt against it, once", () => {
    assert.deepEqual([...attemptedVersionIds(sets)].sort(), ["v1", "v2"]);
  });

  it("offers a station with attempts left, even if another set exhausted it", () => {
    assert.deepEqual(incompleteVersionIds(sets, 3).sort(), ["v1", "v2"]);
  });

  it("drops a station that has used its whole allowance", () => {
    const exhausted = [set({ entries: [entry("v1", 3)] })];
    assert.deepEqual(incompleteVersionIds(exhausted, 3), []);
  });
});

describe("chooseStations", () => {
  const library = [{ version_id: "a" }, { version_id: "b" }, { version_id: "c" }];

  it("prefers stations the candidate has not seen", () => {
    const picked = chooseStations(library, 2, { excludeVersionIds: new Set(["a"]) });
    assert.equal(picked.length, 2);
    assert.ok(!picked.some((station) => station.version_id === "a"));
  });

  it("falls back to the whole library rather than returning too few", () => {
    const picked = chooseStations(library, 3, { excludeVersionIds: new Set(["a", "b"]) });
    assert.equal(picked.length, 3);
  });
});

/** A minimal attempt record for `stationFeedbackState` and `attemptsWithTranscript`. */
function attempt(
  status: AttemptStatusRecord["status"],
  over: Partial<AttemptStatusRecord> = {},
): AttemptStatusRecord {
  return {
    status,
    has_result: false,
    created_at: "2026-01-01T00:00:00Z",
    ...over,
  };
}

describe("stationFeedbackState", () => {
  it("reads not_attempted when there is no attempt at all", () => {
    assert.equal(stationFeedbackState([]), "not_attempted");
  });

  it("reads not_attempted for a station opened and left at created", () => {
    assert.equal(stationFeedbackState([attempt("created")]), "not_attempted");
  });

  it("reads not_attempted for a station left mid-consultation at running", () => {
    assert.equal(stationFeedbackState([attempt("running")]), "not_attempted");
  });

  it("reads marking for a finished consultation still waiting on its result", () => {
    assert.equal(stationFeedbackState([attempt("interaction_complete")]), "marking");
  });

  it("reads review once a result exists, regardless of status", () => {
    assert.equal(
      stationFeedbackState([attempt("interaction_complete", { has_result: true })]),
      "review",
    );
  });

  it("reads failed for an attempt the worker gave up on", () => {
    assert.equal(stationFeedbackState([attempt("failed")]), "failed");
  });

  it("picks the most recent attempt when there are several", () => {
    const attempts = [
      attempt("failed", { created_at: "2026-01-01T00:00:00Z" }),
      attempt("interaction_complete", { created_at: "2026-01-03T00:00:00Z" }),
      attempt("created", { created_at: "2026-01-02T00:00:00Z" }),
    ];
    assert.equal(stationFeedbackState(attempts), "marking");
  });

  it("keeps earlier feedback reachable after the station is opened again and left", () => {
    const attempts = [
      attempt("evaluated", { has_result: true, created_at: "2026-01-01T00:00:00Z" }),
      attempt("created", { created_at: "2026-01-02T00:00:00Z" }),
    ];
    assert.equal(stationFeedbackState(attempts), "review");
  });

  it("keeps earlier feedback reachable after a later run fails", () => {
    const attempts = [
      attempt("evaluated", { has_result: true, created_at: "2026-01-01T00:00:00Z" }),
      attempt("failed", { created_at: "2026-01-02T00:00:00Z" }),
    ];
    assert.equal(stationFeedbackState(attempts), "review");
  });
});

describe("anyStationMarking", () => {
  it("is true when at least one row is marking", () => {
    assert.equal(anyStationMarking(["not_attempted", "marking", "review"]), true);
  });

  it("is false once nothing is marking", () => {
    assert.equal(anyStationMarking(["not_attempted", "review", "failed"]), false);
  });

  it("is false for an empty list", () => {
    assert.equal(anyStationMarking([]), false);
  });
});

describe("attemptsWithTranscript", () => {
  it("drops an attempt that never finished the consultation", () => {
    const attempts = [attempt("created"), attempt("running")];
    assert.deepEqual(attemptsWithTranscript(attempts), []);
  });

  it("keeps interaction_complete, evaluated and failed attempts", () => {
    const attempts = [
      attempt("created"),
      attempt("interaction_complete"),
      attempt("evaluated"),
      attempt("failed"),
    ];
    assert.deepEqual(
      attemptsWithTranscript(attempts).map((item) => item.status),
      ["interaction_complete", "evaluated", "failed"],
    );
  });
});

describe("checkMilestone", () => {
  it("fires on crossing a five", () => {
    assert.deepEqual(checkMilestone(10, 9), { reached: true, milestone: 10, stationBadges: 2 });
  });

  it("stays quiet in between", () => {
    assert.equal(checkMilestone(11, 10).reached, false);
  });
});
