import assert from "node:assert/strict";
import { afterEach, test } from "node:test";
import { revokeSession } from "@/foundation/platform-client/revokeSession";

const realFetch = globalThis.fetch;
const API = "http://api.test";
const NOW = 1_000_000_000;

interface Call {
  path: string;
  authorization: string | null;
  body: unknown;
}

/** A platform-api that accepts `liveAccess` only and renews `liveRefresh` once. */
function fakeApi(liveAccess: string, liveRefresh: string): Call[] {
  const calls: Call[] = [];
  globalThis.fetch = (async (input: string | URL | Request, init?: RequestInit) => {
    const path = String(input).replace(API, "");
    const headers = new Headers(init?.headers);
    const body: unknown = JSON.parse(String(init?.body ?? "null"));
    calls.push({ path, authorization: headers.get("Authorization"), body });
    if (path === "/api/v1/auth/refresh") {
      const presented = (body as { refresh_token: string }).refresh_token;
      if (presented !== liveRefresh) return new Response("{}", { status: 401 });
      return Response.json({ access_token: "at-new", refresh_token: "rt-new", expires_in: 900 });
    }
    const bearer = headers.get("Authorization");
    if (bearer !== `Bearer ${liveAccess}` && bearer !== "Bearer at-new") {
      return new Response("{}", { status: 401 });
    }
    return new Response(null, { status: 204 });
  }) as typeof fetch;
  return calls;
}

afterEach(() => {
  globalThis.fetch = realFetch;
});

test("signing out sends the bearer with the refresh token, so the chain is revoked", async () => {
  const calls = fakeApi("at-1", "rt-1");
  const outcome = await revokeSession(API, { accessToken: "at-1", refreshToken: "rt-1", expiresAt: NOW + 600_000 }, NOW);
  assert.equal(outcome, "revoked");
  assert.deepEqual(calls, [
    { path: "/api/v1/auth/logout", authorization: "Bearer at-1", body: { refresh_token: "rt-1" } },
  ]);
});

test("an expired access token is renewed first and the logout carries the new pair", async () => {
  const calls = fakeApi("at-1", "rt-1");
  const outcome = await revokeSession(API, { accessToken: "at-1", refreshToken: "rt-1", expiresAt: NOW - 1 }, NOW);
  assert.equal(outcome, "revoked");
  assert.deepEqual(
    calls.map((c) => [c.path, c.authorization, c.body]),
    [
      ["/api/v1/auth/refresh", null, { refresh_token: "rt-1" }],
      ["/api/v1/auth/logout", "Bearer at-new", { refresh_token: "rt-new" }],
    ],
  );
});

test("a 401 from logout is not taken as signed out: it renews and tries again", async () => {
  const calls = fakeApi("someone-elses", "rt-1");
  const outcome = await revokeSession(API, { accessToken: "at-stale", refreshToken: "rt-1", expiresAt: NOW + 600_000 }, NOW);
  assert.equal(outcome, "revoked");
  assert.deepEqual(calls.map((c) => c.path), ["/api/v1/auth/logout", "/api/v1/auth/refresh", "/api/v1/auth/logout"]);
});

test("a chain that can no longer be renewed is reported, not passed off as revoked", async () => {
  fakeApi("other", "rt-other");
  const outcome = await revokeSession(API, { accessToken: "at-1", refreshToken: "rt-spent", expiresAt: NOW - 1 }, NOW);
  assert.equal(outcome, "refused");
});
