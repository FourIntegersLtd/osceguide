import assert from "node:assert/strict";
import { afterEach, it } from "node:test";
import { readResultPreview, saveDecision } from "@/domains/assess/results/api";

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

it("saves a decision without a recruitment_outcome key when the form has no such field, and with null when it was cleared", async () => {
  const bodies: Record<string, unknown>[] = [];
  globalThis.fetch = (async (_input: unknown, init?: RequestInit) => {
    bodies.push(JSON.parse(String(init?.body)) as Record<string, unknown>);
    return new Response("{}", { status: 200, headers: { "content-type": "application/json" } });
  }) as typeof fetch;
  await saveDecision("kings", "sit-1", "tr-9", { assessmentOutcome: "pass", rationale: "ok", expectedRevision: 2 });
  await saveDecision("kings", "sit-1", "tr-9", { assessmentOutcome: "pass", recruitmentOutcome: null, rationale: "ok", expectedRevision: 2 });
  assert.equal("recruitment_outcome" in (bodies[0] ?? {}), false);
  assert.equal(bodies[1]?.recruitment_outcome, null);
});
