import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { MAX_DURATION_MS, toastDurationMs } from "./toastDuration";

describe("toastDurationMs", () => {
  it("caps an explicit duration at 60 seconds", () => {
    const ms = toastDurationMs({ durationMs: 10 * 60_000 }, "success");
    assert.equal(ms, 60_000);
    assert.ok(ms <= MAX_DURATION_MS);
  });

  it("keeps 4.5 s by default and 8 s for errors", () => {
    assert.equal(toastDurationMs({}, "success"), 4500);
    assert.equal(toastDurationMs({}, "error"), 8000);
  });

  it("honours an explicit duration over the tone default", () => {
    assert.equal(toastDurationMs({ durationMs: 20_000 }, "success"), 20_000);
  });
});
