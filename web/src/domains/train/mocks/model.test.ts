import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { PlatformError } from "@/foundation/platform-client";
import type { StationSet } from "@/domains/train/api";
import {
  anyStationMarking,
  attemptedVersionIds,
  attemptsWithTranscript,
  checkMilestone,
  combineIntro,
  chooseStations,
  flaggedEntryPath,
  groupSets,
  incompleteVersionIds,
  stationRowState,
  rowStatusLabel,
  canStartSession,
  sessionAction,
  sessionMinutes,
  sessionState,
  stationFeedbackState,
  type AttemptStatusRecord,
  describeCreateSetFailure,
  nothingPickableMessage,
  BEFORE_YOU_START,
  mockRules,
  pickerMax,
  sessionUpdatedMessage,
  stationLabel,
  trialStationsHint,
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

  it("offers nothing when the exam's attempt limit is unknown, rather than guessing one", () => {
    assert.deepEqual(incompleteVersionIds(sets, null), []);
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

describe("flaggedEntryPath", () => {
  it("reopens the session entry a station was flagged in", () => {
    assert.equal(flaggedEntryPath({ set_id: "set1", entry_id: "e2" }), "/mocks/set1/stations/e2");
  });
});

describe("nothingPickableMessage", () => {
  const trial = { stations: 5, days: 21, attempts_per_station: 2 };

  it("quotes the trial limits the server sent when the free trial is used up", () => {
    assert.equal(
      nothingPickableMessage({ hasPaid: false, subscriptionExpired: false, trial }),
      "Your free trial is used up. It covers 5 stations, each sat up to 2 times, within 21 days of signing up. Subscribe to keep practising.",
    );
  });

  it("tells a lapsed subscriber their access has ended", () => {
    assert.match(
      nothingPickableMessage({ hasPaid: false, subscriptionExpired: true, trial }),
      /access to this exam has ended/,
    );
  });

  it("says the exam is empty for someone with access", () => {
    assert.match(
      nothingPickableMessage({ hasPaid: true, subscriptionExpired: false, trial }),
      /no stations for this exam yet/,
    );
  });
});

describe("describeCreateSetFailure", () => {
  const refusal = (status: number, code: string, details?: Record<string, unknown>) =>
    new PlatformError(status, { code, message: "server wording", details } as ConstructorParameters<typeof PlatformError>[1]);

  it("gives each refusal its own sentence, never 'Error creating mock'", () => {
    assert.match(describeCreateSetFailure(refusal(403, "not_entitled", { reason: "trial_exhausted" })), /used up/);
    assert.match(describeCreateSetFailure(refusal(409, "set_locked")), /locked/);
    assert.match(describeCreateSetFailure(refusal(409, "station_not_published")), /not available/);
  });

  it("falls back to the server's message, then a generic sentence", () => {
    assert.equal(describeCreateSetFailure(refusal(500, "internal_error")), "server wording");
    assert.equal(describeCreateSetFailure(undefined), "We could not create this session. Please try again.");
  });
});

describe("trial_station_limit", () => {
  const limit = (stationsLeft: number) =>
    new PlatformError(403, {
      code: "trial_station_limit",
      message: "server wording",
      details: { stations_left: stationsLeft },
    } as ConstructorParameters<typeof PlatformError>[1]);

  it("says how many free stations are left", () => {
    assert.equal(
      describeCreateSetFailure(limit(2)),
      "Your free trial has 2 stations left. Choose 2 or fewer new stations, or subscribe for more.",
    );
    assert.equal(
      describeCreateSetFailure(limit(0)),
      "Your free trial has no stations left. Subscribe to add new stations.",
    );
  });
});

describe("session setup copy", () => {
  it("does not ask for equipment the learner has to buy", () => {
    assert.deepEqual(BEFORE_YOU_START, [
      "The built-in microphone on your laptop or phone is fine",
      "Headphones are optional. They cut down echo",
      "Find somewhere you can talk without interruptions, with a stable connection",
    ]);
  });

  it("caps the picker at the free stations left, and only on the trial", () => {
    assert.equal(pickerMax(40, 2), 2);
    assert.equal(pickerMax(1, 3), 1);
    assert.equal(pickerMax(40, null), 40);
  });

  it("tells a trial learner how many stations they have left", () => {
    assert.equal(trialStationsHint(2), "Your free trial has 2 stations left.");
    assert.equal(trialStationsHint(1), "Your free trial has 1 station left.");
    assert.equal(trialStationsHint(0), "Your free trial has no stations left.");
    assert.equal(trialStationsHint(null), null);
  });
});

describe("mockRules", () => {
  it("reads as four plain instructions, with the clock described correctly", () => {
    assert.deepEqual(mockRules(3), [
      "You talk to an AI patient out loud. The built-in microphone on your laptop or phone is fine. Headphones are optional. They cut down echo.",
      "Each station follows the same format. About halfway through, a prompt tells you to move from history taking to management.",
      "Find somewhere you can talk without interruptions, with a stable connection. If something goes wrong, flag the station and message support.",
      "You can attempt each station up to 3 times. Each station opens with reading time, and the consultation starts when you press Start simulation or reading time runs out.",
    ]);
    assert.match(mockRules(null)[3] ?? "", /^Each station opens with reading time/);
    assert.match(mockRules(1)[3] ?? "", /^You can attempt each station once\./);
  });
});

describe("stationLabel", () => {
  it("names a station only once it has been sat", () => {
    assert.equal(stationLabel({ station_title: null }, 0), "Station 1");
    assert.equal(stationLabel({ station_title: undefined }, 3), "Station 4");
    assert.equal(stationLabel({ station_title: "Chest pain" }, 1), "Chest pain");
  });
});

describe("sessionUpdatedMessage", () => {
  it("confirms the save with the station count", () => {
    assert.equal(sessionUpdatedMessage(4), "Session updated: 4 stations");
    assert.equal(sessionUpdatedMessage(1), "Session updated: 1 station");
  });
});

describe("combineIntro", () => {
  it("invites a pick once stations were sat, and says what unlocks it before", () => {
    assert.equal(combineIntro(true), "Pick the stations you found hardest and sit them again as one session.");
    assert.match(combineIntro(false), /^Available once you have sat a few stations/);
  });
});

describe("stationRowState", () => {
  it("fails closed when the exam's limit is unknown and attempts were made", () => {
    assert.deepEqual(stationRowState({ attempts: 3 }, false, null), {
      status: "unknown",
      canAttempt: false,
      canReviewLast: true,
    });
  });
  it("offers no start on a never-attempted entry whose exam is retired", () => {
    assert.deepEqual(stationRowState({ attempts: 0 }, false, null), {
      status: "not_attempted",
      canAttempt: false,
      canReviewLast: false,
    });
  });
  it("completes at the limit and counts below it", () => {
    assert.equal(stationRowState({ attempts: 3 }, false, 3).status, "completed");
    assert.equal(stationRowState({ attempts: 3 }, false, 3).canAttempt, false);
    assert.deepEqual(stationRowState({ attempts: 1 }, false, 3), {
      status: "counting",
      canAttempt: true,
      canReviewLast: false,
    });
  });
  it("offers nothing new on a locked set", () => {
    assert.equal(stationRowState({ attempts: 1 }, true, 3).canAttempt, false);
    assert.equal(stationRowState({ attempts: 1 }, true, 3).canReviewLast, true);
  });
});

describe("rowStatusLabel", () => {
  it("says only what is known when the limit is unknown", () => {
    assert.equal(rowStatusLabel("unknown", 3, null), "3 attempts made");
    assert.equal(rowStatusLabel("unknown", 1, null), "1 attempt made");
  });
  it("shows the count against a known limit", () => {
    assert.equal(rowStatusLabel("counting", 1, 3), "1/3 attempts");
    assert.equal(rowStatusLabel("not_attempted", 0, null), "Not attempted");
  });
});

describe("canStartSession", () => {
  it("never offers the hero start for a retired exam", () => {
    assert.equal(canStartSession({ examOffered: false, attempted: false, locked: false }), false);
  });
  it("offers it for a fresh, unlocked set on an offered exam only", () => {
    assert.equal(canStartSession({ examOffered: true, attempted: false, locked: false }), true);
    assert.equal(canStartSession({ examOffered: true, attempted: true, locked: false }), false);
    assert.equal(canStartSession({ examOffered: true, attempted: false, locked: true }), false);
  });
});
