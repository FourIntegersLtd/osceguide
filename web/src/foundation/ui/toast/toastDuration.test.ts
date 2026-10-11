import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { PERSISTENT_CAP_MS, toastDurationMs } from "./toastDuration";

describe("toastDurationMs", () => {
  it("dismisses a persistent success toast within 60 seconds", () => {
    const ms = toastDurationMs({ persistent: true }, "success");
    assert.equal(ms, 60_000);
    assert.ok(ms <= PERSISTENT_CAP_MS);
  });

  it("keeps 4.5 s by default and 8 s for errors", () => {
    assert.equal(toastDurationMs({}, "success"), 4500);
    assert.equal(toastDurationMs({}, "error"), 8000);
  });

  it("honours an explicit duration when not persistent", () => {
    assert.equal(toastDurationMs({ durationMs: 20_000 }, "success"), 20_000);
  });
});
