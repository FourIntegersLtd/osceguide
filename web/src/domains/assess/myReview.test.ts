import assert from "node:assert/strict";
import { afterEach, describe, it } from "node:test";
import { readMySlotReview } from "@/domains/assess/api";

const realFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = realFetch;
});

function respond(status: number, body: unknown) {
  globalThis.fetch = (async () =>
    new Response(JSON.stringify(body), {
      status,
      headers: { "content-type": "application/json" },
    })) as typeof fetch;
}

describe("an examiner's own slot review", () => {
  it("is read directly when the route is served", async () => {
    respond(200, { id: "r1", submitted_by: "me", status: "draft" });
    assert.equal((await readMySlotReview("kings", "s1"))?.id, "r1");
  });

  it("is null when there is none yet", async () => {
    respond(200, null);
    assert.equal(await readMySlotReview("kings", "s1"), null);
  });

  it("fails rather than reading as no review", async () => {
    respond(403, { code: "forbidden", message: "No" });
    await assert.rejects(() => readMySlotReview("kings", "s1"));
  });
});
