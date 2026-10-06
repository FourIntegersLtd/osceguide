import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { matchesStatusFilter, parseStatusFilter, stationListUrl } from "./stationListUrl";

describe("stationListUrl", () => {
  it("reads only the known filters and falls back to active", () => {
    assert.equal(parseStatusFilter("archived"), "archived");
    assert.equal(parseStatusFilter("all"), "all");
    assert.equal(parseStatusFilter("nonsense"), "active");
    assert.equal(parseStatusFilter(null), "active");
  });

  it("writes the filter and the open station, and nothing for the default", () => {
    assert.equal(stationListUrl("/authoring/stations", { status: "active" }), "/authoring/stations");
    assert.equal(
      stationListUrl("/authoring/stations", { status: "archived", station: "abc" }),
      "/authoring/stations?status=archived&station=abc",
    );
    assert.equal(
      stationListUrl("/authoring/stations", { status: "active", station: "abc" }),
      "/authoring/stations?station=abc",
    );
  });

  it("keeps archived rows out of Active and nothing else out of Archived", () => {
    assert.equal(matchesStatusFilter("archived", "active"), false);
    assert.equal(matchesStatusFilter("draft", "active"), true);
    assert.equal(matchesStatusFilter("published", "archived"), false);
    assert.equal(matchesStatusFilter("archived", "archived"), true);
    assert.equal(matchesStatusFilter("archived", "all"), true);
  });
});
