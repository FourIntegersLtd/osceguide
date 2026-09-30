import assert from "node:assert/strict";
import { afterEach, describe, it } from "node:test";
import { joinCircuit } from "@/domains/assess/trainee/api";

const realFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = realFetch;
});

interface Call {
  url: string;
  method: string;
}

function record(status: number, body: unknown): Call[] {
  const calls: Call[] = [];
  globalThis.fetch = (async (input: unknown, init?: RequestInit) => {
    calls.push({ url: String(input), method: init?.method ?? "GET" });
    return new Response(JSON.stringify(body), {
      status,
      headers: { "content-type": "application/json" },
    });
  }) as typeof fetch;
  return calls;
}

describe("joining a circuit", () => {
  it("asks for the room grant with a POST, the verb the route answers", async () => {
    /*
     * The backend mints the grant on `POST /me/circuits/{id}/join-token`
     * (sittings/router_run.py) and serves no GET. The client defaults to
     * GET, so an omitted `method` here silently 405s every exam-day join.
     */
    const calls = record(200, { token: "t", server_url: "wss://x", room: "r" });
    await joinCircuit("c1");

    assert.equal(calls.length, 1);
    assert.ok(calls[0]?.url.endsWith("/api/v1/me/circuits/c1/join-token"));
    assert.equal(calls[0]?.method, "POST");
  });
});
