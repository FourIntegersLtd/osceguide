import assert from "node:assert/strict";
import { afterEach, describe, it } from "node:test";
import { passRateLabel, readOrgReporting } from "@/domains/assess/reporting/api";

const realFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = realFetch;
});

describe("institution reporting", () => {
  it("reads the organisation's cross-sitting summary", async () => {
    const urls: string[] = [];
    globalThis.fetch = (async (input: unknown) => {
      urls.push(String(input));
      return new Response(JSON.stringify({ programmes: [] }), { status: 200, headers: { "content-type": "application/json" } });
    }) as typeof fetch;
    assert.deepEqual(await readOrgReporting("kings"), { programmes: [] });
    assert.ok(urls[0]?.endsWith("/api/v1/orgs/kings/reporting"));
  });

  it("says nothing is released yet rather than a pass rate of zero", () => {
    assert.equal(passRateLabel({ released: 0, passed: 0, pass_rate: null }), "Nothing released yet");
    assert.equal(passRateLabel({ released: 4, passed: 3, pass_rate: 75 }), "75% (3 of 4 released)");
  });
});
