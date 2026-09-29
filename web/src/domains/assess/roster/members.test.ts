import assert from "node:assert/strict";
import { afterEach, describe, it } from "node:test";
import { readGroupMembers } from "@/domains/assess/roster/api";

const realFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = realFetch;
});

describe("a group's members", () => {
  it("are read from the members route, every page of it", async () => {
    const seen: string[] = [];
    globalThis.fetch = (async (input: RequestInfo | URL) => {
      const url = String(input);
      seen.push(url);
      const body = url.includes("cursor=next")
        ? { items: [{ id: "t3" }], next_cursor: null }
        : { items: [{ id: "t1" }, { id: "t2" }], next_cursor: "next" };
      return new Response(JSON.stringify(body), { status: 200 });
    }) as typeof fetch;

    assert.deepEqual(await readGroupMembers("kings", "g1"), ["t1", "t2", "t3"]);
    assert.ok(seen.every((url) => url.includes("/trainee-groups/g1/members")));
    assert.equal(seen.length, 2);
  });

  it("fails rather than reading as an empty group", async () => {
    globalThis.fetch = (async () =>
      new Response(JSON.stringify({ code: "group_not_found", message: "No such group" }), {
        status: 404,
      })) as typeof fetch;
    await assert.rejects(() => readGroupMembers("kings", "gone"));
  });
});
