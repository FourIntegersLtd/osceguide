import assert from "node:assert/strict";
import { afterEach, describe, it } from "node:test";
import { memberIdsOf, readGroupMembers } from "@/domains/assess/roster/api";

const realFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = realFetch;
});

function answer(routes: Record<string, { status: number; body: unknown }>): string[] {
  const seen: string[] = [];
  globalThis.fetch = (async (input: RequestInfo | URL) => {
    const url = String(input);
    seen.push(url);
    const hit = Object.entries(routes).find(([path]) => url.includes(path));
    const { status, body } = hit ? hit[1] : { status: 404, body: { detail: "Not Found" } };
    return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
  }) as typeof fetch;
  return seen;
}

describe("a group's members", () => {
  it("reads the members route when it is served", async () => {
    const seen = answer({ "/members": { status: 200, body: { trainee_ids: ["t1", "t2"] } } });
    assert.deepEqual(await readGroupMembers("kings", "g1"), ["t1", "t2"]);
    assert.equal(seen.some((url) => url.includes("/roster/resolve")), false);
  });

  it("falls back to resolving the roster where the route is not deployed", async () => {
    const seen = answer({ "/roster/resolve": { status: 200, body: { trainee_ids: ["t3"], warnings: [] } } });
    assert.deepEqual(await readGroupMembers("kings", "g1"), ["t3"]);
    assert.ok(seen.some((url) => url.includes("/roster/resolve")));
  });

  it("does not paper over a real refusal with the fallback", async () => {
    answer({ "/members": { status: 404, body: { code: "group_not_found", message: "No such group" } } });
    await assert.rejects(() => readGroupMembers("kings", "gone"));
  });

  it("reads a page of trainees as well as a list of ids", () => {
    assert.deepEqual(memberIdsOf({ items: [{ id: "a" }, { trainee_id: "b" }], next_cursor: null }), [
      "a",
      "b",
    ]);
    assert.throws(() => memberIdsOf({ something: "else" }));
  });
});
