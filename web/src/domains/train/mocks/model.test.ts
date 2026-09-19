import assert from "node:assert/strict";
import { describe, it } from "node:test";
import type { StationSet } from "@/domains/train/api";
import {
  attemptedVersionIds,
  checkMilestone,
  chooseStations,
  groupSets,
  incompleteVersionIds,
  sessionAction,
  sessionMinutes,
  sessionState,
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

  it("turns a finished session over to Review", () => {
    const done = set({ attempted_entries: 3, total_entries: 3, completed_at: "2026-01-01T00:00:00Z" });
    assert.equal(sessionState(done), "completed");
    assert.equal(sessionAction(done), "Review");
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

describe("checkMilestone", () => {
  it("fires on crossing a five", () => {
    assert.deepEqual(checkMilestone(10, 9), { reached: true, milestone: 10, stationBadges: 2 });
  });

  it("stays quiet in between", () => {
    assert.equal(checkMilestone(11, 10).reached, false);
  });
});
