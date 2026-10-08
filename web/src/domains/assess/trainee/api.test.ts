import assert from "node:assert/strict";
import { afterEach, describe, it } from "node:test";
import {
  joinCircuit,
  mySittingsStreamPath,
  readMySittings,
  reviewIfReady,
  reviewWaitingCopy,
  stationScoreLabel,
} from "@/domains/assess/trainee/api";

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

describe("one workspace's sittings", () => {
  it("asks the api for only that organisation's", async () => {
    const calls = record(200, { items: [] });
    await readMySittings("kings");
    assert.ok(calls[0]?.url.endsWith("/api/v1/me/sittings?org_slug=kings"));
  });

  it("names the organisation on the stream too, and reads everything when there is none", () => {
    assert.equal(mySittingsStreamPath("kings"), "/api/v1/me/sittings/stream?org_slug=kings");
    assert.equal(mySittingsStreamPath(null), "/api/v1/me/sittings/stream");
  });
});

it("a waiting review answer carries its reason, a ready one is the review", () => {
  assert.equal(reviewIfReady({ slot_id: "s1", state: "not_released" }), null);
  assert.deepEqual(reviewWaitingCopy("not_released").title, "Not released yet");
  assert.deepEqual(reviewWaitingCopy("not_marked").title, "Not marked yet");
});

it("a station's score reads as a mark and a pass word only when the rubric has a rule", () => {
  const base = { slot_id: "s1", station_title: "Chest pain" };
  assert.equal(stationScoreLabel({ ...base, score: null, passed: null }), "Not scored");
  assert.equal(stationScoreLabel({ ...base, score: 66, passed: null }), "66 / 100");
  assert.equal(stationScoreLabel({ ...base, score: 41.4, passed: false }), "41 / 100 · Fail");
});
