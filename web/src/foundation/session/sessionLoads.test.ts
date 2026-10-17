import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { sessionLoads } from "@/foundation/session/sessionLoads";

/** A load whose answer is whichever token is stored when it starts, settled by hand. */
function fakeLoads() {
  let token = "old";
  const pending: Array<() => void> = [];
  let started = 0;
  const load = () => {
    started += 1;
    const seen = token;
    return new Promise<string>((resolve) => pending.push(() => resolve(seen)));
  };
  return {
    load,
    store: (next: string) => (token = next),
    settleNext: async () => {
      while (pending.length === 0) await Promise.resolve();
      pending.shift()!();
      await Promise.resolve();
    },
    started: () => started,
  };
}

describe("session loads", () => {
  it("joins the load already in flight for background re-checks", async () => {
    const fake = fakeLoads();
    const loads = sessionLoads(fake.load);
    const a = loads.join();
    const b = loads.join();
    assert.equal(a, b);
    await fake.settleNext();
    assert.equal(await a, "old");
    assert.equal(fake.started(), 1);
  });

  it("answers a refresh after sign-in from the new tokens, not a load started before them", async () => {
    const fake = fakeLoads();
    const loads = sessionLoads(fake.load);
    const stale = loads.join(); // the retry timer or the 401 handler, before login stored tokens
    fake.store("new");
    const fresh = loads.after();
    await fake.settleNext();
    assert.equal(await stale, "old");
    await fake.settleNext();
    assert.equal(await fresh, "new");
    assert.equal(fake.started(), 2);
  });

  it("starts at once when nothing is in flight, and callers after it share the queued load", async () => {
    const fake = fakeLoads();
    const loads = sessionLoads(fake.load);
    fake.store("new");
    const first = loads.after();
    await fake.settleNext();
    assert.equal(await first, "new");
    loads.join();
    const x = loads.after();
    const y = loads.after();
    assert.equal(x, y);
  });
});
