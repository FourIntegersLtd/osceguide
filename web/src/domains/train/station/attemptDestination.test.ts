import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { attemptDestination, setStationState } from "@/domains/train/station/attemptDestination";

describe("attemptDestination", () => {
  it("reads a session's station inside its session, never at the single-practice page", () => {
    assert.deepEqual(attemptDestination({ station_id: "s", set_entry_id: "e" }, "set-1"), {
      kind: "set_entry",
      setId: "set-1",
      entryId: "e",
    });
    assert.deepEqual(attemptDestination({ station_id: "s", set_entry_id: "e" }, null), { kind: "unknown" });
  });

  it("never links /stations/null", () => {
    assert.deepEqual(attemptDestination({ station_id: null }, null), { kind: "unknown" });
    assert.deepEqual(attemptDestination({ station_id: "s" }, null), { kind: "station", stationId: "s" });
  });
});

describe("setStationState", () => {
  it("names an entry the session does not have and a station that was retired", () => {
    assert.equal(setStationState({ entry: null, station: null, action: "attempt" }), "unknown_entry");
    assert.equal(setStationState({ entry: {}, station: undefined, action: "attempt" }), "retired");
    assert.equal(setStationState({ entry: {}, station: undefined, action: "review" }), "ok");
    assert.equal(setStationState({ entry: {}, station: {}, action: "attempt" }), "ok");
  });
});
