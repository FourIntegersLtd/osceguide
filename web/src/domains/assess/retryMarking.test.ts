import assert from "node:assert/strict";
import { afterEach, describe, it } from "node:test";
import { retrySlotMarking } from "@/domains/assess/api";

const realFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = realFetch;
});

describe("retrySlotMarking", () => {
  it("posts to the organisation's slot and returns whether it was queued", async () => {
    let seen = "";
    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      seen = `${init?.method} ${String(input)}`;
      return new Response(JSON.stringify({ queued: true, policy_version: "platform-default@1", reason: null }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }) as typeof fetch;
    const result = await retrySlotMarking("kings", "s1");
    assert.equal(result.queued, true);
    assert.match(seen, /^POST .*\/orgs\/kings\/slots\/s1\/marking\/retry$/);
  });
});
