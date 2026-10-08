import assert from "node:assert/strict";
import { afterEach, describe, it } from "node:test";
import { issueScimToken, revokeScimToken } from "@/domains/assess/api";

const realFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = realFetch;
});

describe("SCIM tokens", () => {
  it("are issued by label and revoked by id", async () => {
    const calls: string[] = [];
    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      calls.push(`${init?.method} ${new URL(String(input), "http://x").pathname} ${init?.body ?? ""}`);
      return init?.method === "DELETE"
        ? new Response(null, { status: 204 })
        : new Response(JSON.stringify({ id: "t1", label: "Entra", token: "scim_abc", token_prefix: "scim_a" }), {
            status: 201,
            headers: { "content-type": "application/json" },
          });
    }) as typeof fetch;
    assert.equal((await issueScimToken("kings", "Entra")).token, "scim_abc");
    await revokeScimToken("kings", "t1");
    assert.deepEqual(calls.map((call) => call.replace(/^(\w+) .*?(\/orgs\/)/, "$1 $2")), [
      'POST /orgs/kings/scim/tokens {"label":"Entra"}',
      "DELETE /orgs/kings/scim/tokens/t1 ",
    ]);
  });
});
