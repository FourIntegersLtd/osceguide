import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { achievementsView } from "@/capabilities/account/achievementsView";

const none = { stationCount: 0, currentStreak: 0, streakBadgeCount: 0, longestStreak: null };

describe("achievementsView", () => {
  it("has no latest badge and a first-badge nudge for a beginner", () => {
    const view = achievementsView(none);
    assert.equal(view.latest, null);
    assert.equal(view.streaks.longest, null);
    assert.equal(view.nudge, "Five more stations earn your first badge. Practise three days in a row to start a streak.");
  });

  it("names the newest station badge and shows progress to the next", () => {
    const view = achievementsView({ ...none, stationCount: 12, currentStreak: 2 });
    assert.equal(view.stations.badges, 2);
    assert.equal(view.stations.nextShare, 40);
    assert.equal(view.latest, "Station badge 10");
    assert.equal(view.nudge, "Three more stations earn your next badge. Practise tomorrow to keep the streak.");
  });

  it("falls back to a streak badge when no station badge is earned, and keeps the longest streak as a stat", () => {
    const view = achievementsView({
      ...none,
      stationCount: 3,
      streakBadgeCount: 1,
      longestStreak: { length: 4, startDate: "2026-10-01", endDate: "2026-10-04" },
    });
    assert.equal(view.latest, "Streak badge");
    assert.deepEqual(view.streaks.longest, { days: 4, start: "2026-10-01", end: "2026-10-04" });
  });

  it("treats a zero-length longest streak as none", () => {
    const view = achievementsView({ ...none, longestStreak: { length: 0, startDate: "2026-10-01", endDate: "2026-10-01" } });
    assert.equal(view.streaks.longest, null);
  });
});
