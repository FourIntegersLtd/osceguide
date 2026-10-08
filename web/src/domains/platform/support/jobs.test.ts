import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { jobRunningLabel, mergeOlderJobs, type JobLike } from "@/domains/platform/support/jobs";

const now = new Date("2026-10-08T12:00:00Z");

function job(id: number, status: string, startedAt?: string): JobLike {
  return { id, status, events: startedAt ? [{ type: "started", at: startedAt }] : [] };
}

describe("background task age", () => {
  it("says how long a running task has been running, and whether that is long enough to cancel", () => {
    assert.deepEqual(jobRunningLabel(job(1, "doing", "2026-10-08T11:46:00Z"), now), {
      text: "Running for 14 min",
      cancellable: true,
    });
    assert.deepEqual(jobRunningLabel(job(2, "doing", "2026-10-08T11:58:00Z"), now), {
      text: "Running for 2 min",
      cancellable: false,
    });
    assert.deepEqual(jobRunningLabel(job(3, "doing", "2026-10-08T09:55:00Z"), now), {
      text: "Running for 2 h 5 min",
      cancellable: true,
    });
  });

  it("says nothing about a task that is not running", () => {
    assert.equal(jobRunningLabel(job(4, "failed", "2026-10-08T11:00:00Z"), now), null);
    assert.equal(jobRunningLabel(job(5, "doing"), now), null);
  });
});

describe("paging past the first fifty", () => {
  it("appends older tasks and drops any the live page already shows", () => {
    const first = [job(9, "failed"), job(8, "failed")];
    const older = [job(8, "failed"), job(7, "failed")];
    assert.deepEqual(
      mergeOlderJobs(first, older).map((entry) => entry.id),
      [9, 8, 7],
    );
  });
});
