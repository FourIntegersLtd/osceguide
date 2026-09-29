import assert from "node:assert/strict";
import { afterEach, describe, it } from "node:test";
import { readCircuitReview } from "@/domains/assess/sessions/api";

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

const REVIEW = { id: "r1", circuit_id: "c1", merged_notes: "Well run", finalized_at: "2026-09-29T09:00:00Z" };

describe("whether a circuit's feedback was published", () => {
  it("is published when the server has a finalised review", async () => {
    respond(200, REVIEW);
    const result = await readCircuitReview("kings", "c1");
    assert.equal(result.state, "published");
  });

  it("is not published when there is a draft or no review at all", async () => {
    respond(200, { ...REVIEW, finalized_at: null });
    assert.equal((await readCircuitReview("kings", "c1")).state, "unpublished");
    respond(404, { code: "review_not_found", message: "No review" });
    assert.equal((await readCircuitReview("kings", "c1")).state, "unpublished");
  });

  it("is unknown, not unpublished, where the read is not deployed", async () => {
    respond(404, { detail: "Not Found" });
    assert.equal((await readCircuitReview("kings", "c1")).state, "unknown");
  });

  it("raises anything else", async () => {
    respond(403, { code: "forbidden", message: "No" });
    await assert.rejects(() => readCircuitReview("kings", "c1"));
  });
});
