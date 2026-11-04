import assert from "node:assert/strict";
import { afterEach, it } from "node:test";
import { readResultPreview } from "@/domains/assess/results/api";

const realFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = realFetch;
});

it("previews a result at the candidate's result-preview route with the roster id", async () => {
  const urls: string[] = [];
  globalThis.fetch = (async (input: unknown) => {
    urls.push(String(input));
    return new Response(JSON.stringify({ assessment_outcome: "pass", stations: [] }), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  }) as typeof fetch;
  const result = await readResultPreview("kings", "sit-1", "tr-9");
  assert.equal(result.assessment_outcome, "pass");
  assert.match(urls[0] ?? "", /\/orgs\/kings\/sittings\/sit-1\/candidates\/tr-9\/result-preview$/);
});
