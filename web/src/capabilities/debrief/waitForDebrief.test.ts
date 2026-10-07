import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { waitForDebrief } from "@/capabilities/debrief/waitForDebrief";

describe("waitForDebrief", () => {
  it("keeps asking until the ended debrief's summary is listed", async () => {
    const answers: string[][] = [[], ["older"], ["mine", "older"]];
    let asked = 0;
    const found = await waitForDebrief(async () => answers[asked++] ?? [], "mine", {
      signal: new AbortController().signal,
      intervalMs: 1,
    });
    assert.equal(found, true);
    assert.equal(asked, 3);
  });

  it("gives up at the deadline, and survives a failed poll", async () => {
    let asked = 0;
    const found = await waitForDebrief(
      async () => {
        asked += 1;
        if (asked === 1) throw new Error("502");
        return ["someone else's"];
      },
      "mine",
      { signal: new AbortController().signal, intervalMs: 5, timeoutMs: 22 },
    );
    assert.equal(found, false);
    assert.ok(asked >= 2);
  });

  it("throws once the polls keep failing, so the screen can say it cannot tell", async () => {
    await assert.rejects(
      waitForDebrief(
        async () => {
          throw new Error("502");
        },
        "mine",
        { signal: new AbortController().signal, intervalMs: 1, maxFailures: 3 },
      ),
      /502/,
    );
  });
});
