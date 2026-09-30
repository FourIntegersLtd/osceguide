import assert from "node:assert/strict";
import { afterEach, describe, it } from "node:test";
import { recordActivity } from "@/capabilities/account/api";

const realFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = realFetch;
});

interface Call {
  url: string;
  method: string;
  body: unknown;
}

function answer(status: number): Call[] {
  const calls: Call[] = [];
  globalThis.fetch = (async (input: unknown, init?: RequestInit) => {
    calls.push({ url: String(input), method: init?.method ?? "GET", body: JSON.parse(String(init?.body)) });
    return new Response(JSON.stringify({ accepted: 1 }), {
      status,
      headers: { "content-type": "application/json" },
    });
  }) as typeof fetch;
  return calls;
}

describe("telling the tutor what was read", () => {
  it("posts one event as a batch, the shape the activity route takes", async () => {
    const calls = answer(202);
    await recordActivity({ kind: "viewed", ref_kind: "summary", ref_id: "asthma", title: "Asthma" });

    assert.equal(calls.length, 1);
    assert.ok(calls[0]?.url.endsWith("/api/v1/me/activity"));
    assert.equal(calls[0]?.method, "POST");
    assert.deepEqual(calls[0]?.body, {
      events: [{ kind: "viewed", ref_kind: "summary", ref_id: "asthma", title: "Asthma" }],
    });
  });

  it("never lets a failed beacon break the page", async () => {
    answer(500);
    await assert.doesNotReject(
      recordActivity({ kind: "listened", ref_kind: "podcast", ref_id: "ep-1", title: "Episode 1" }),
    );
  });
});
