import assert from "node:assert/strict";
import { afterEach, describe, it } from "node:test";
import { bulkAddTrainees, type TraineeInput } from "@/domains/assess/roster/api";

const realFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = realFetch;
});

function rows(count: number): TraineeInput[] {
  return Array.from({ length: count }, (_, index) => ({
    email: `t${index}@example.com`,
    firstName: null,
    lastName: null,
    cohortId: null,
  }));
}

// B-7: a CSV over 500 rows was refused whole with "The request was not valid".
describe("a roster import over 500 rows", () => {
  it("is sent 500 at a time and answered as one result", async () => {
    const sizes: number[] = [];
    globalThis.fetch = (async (_input: RequestInfo | URL, init?: RequestInit) => {
      const sent = (JSON.parse(String(init?.body)) as { trainees: { email: string }[] }).trainees;
      sizes.push(sent.length);
      const body = { created: sent.map((row) => ({ id: row.email, email: row.email })), skipped: [] };
      return new Response(JSON.stringify(body), { status: 201 });
    }) as typeof fetch;

    const result = await bulkAddTrainees("kings", rows(1201));
    assert.deepEqual(sizes, [500, 500, 201]);
    assert.equal(result.created?.length, 1201);
    assert.deepEqual(result.skipped, []);
  });

  it("keeps what was added when a later chunk is refused, and names the rows not sent", async () => {
    let calls = 0;
    globalThis.fetch = (async (_input: RequestInfo | URL, init?: RequestInit) => {
      calls += 1;
      if (calls === 2) {
        return new Response(JSON.stringify({ code: "too_many_requests", message: "Slow down" }), { status: 429 });
      }
      const sent = (JSON.parse(String(init?.body)) as { trainees: { email: string }[] }).trainees;
      return new Response(JSON.stringify({ created: sent.map((row) => ({ email: row.email })), skipped: [] }), {
        status: 201,
      });
    }) as typeof fetch;

    const result = await bulkAddTrainees("kings", rows(1100));
    assert.equal(calls, 2);
    assert.equal(result.created?.length, 500);
    assert.equal(result.skipped?.length, 600);
    assert.deepEqual(result.skipped?.[0], { email: "t500@example.com", code: "too_many_requests" });
  });
});
