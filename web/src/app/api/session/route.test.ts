import assert from "node:assert/strict";
import { test } from "node:test";
import { NextRequest } from "next/server";

import { DELETE, POST } from "@/app/api/session/route";

/** An unsigned token naming a person, enough for the BFF's binding check. */
function jwtFor(sub: string): string {
  const part = (value: object) => Buffer.from(JSON.stringify(value)).toString("base64url");
  return `${part({ alg: "none" })}.${part({ sub })}.sig`;
}

function store(body: object, cookie?: string): NextRequest {
  return new NextRequest("http://localhost:3100/api/session", {
    method: "POST",
    headers: { "content-type": "application/json", ...(cookie ? { cookie } : {}) },
    body: JSON.stringify(body),
  });
}

function setCookies(response: Response): string[] {
  return response.headers.getSetCookie();
}

test("a workspace switch stores the new access token and leaves the refresh cookie alone", async () => {
  // switch-workspace answers with no refresh token: the chain continues.
  const response = await POST(
    store(
      { access_token: jwtFor("user-x"), expires_in: 900 },
      `osce_rt=existing-refresh; osce_at=${jwtFor("user-x")}; osce_session=1`,
    ),
  );
  assert.equal(response.status, 204);
  const cookies = setCookies(response);
  assert.ok(cookies.some((c) => c.startsWith("osce_at=ey")));
  assert.equal(cookies.some((c) => c.startsWith("osce_rt=")), false);
});

test("a token with no refresh token is refused when there is no session to continue", async () => {
  const response = await POST(store({ access_token: jwtFor("user-x"), expires_in: 900 }));
  assert.equal(response.status, 400);
  assert.deepEqual(setCookies(response), []);
});

test("a freshly issued pair still replaces all three cookies", async () => {
  const response = await POST(
    store({ access_token: "a", refresh_token: "r", expires_in: 900 }, "osce_rt=old"),
  );
  assert.equal(response.status, 204);
  const cookies = setCookies(response);
  assert.ok(cookies.some((c) => c.startsWith("osce_rt=r;")));
  assert.ok(cookies.some((c) => c.startsWith("osce_at=a;")));
});

test("a switch by one person never lands beside another person's refresh chain", async () => {
  // Another tab signed in as Y after this tab (X) loaded: the cookies are Y's.
  const response = await POST(
    store(
      { access_token: jwtFor("user-x"), expires_in: 900 },
      `osce_rt=y-refresh; osce_at=${jwtFor("user-y")}; osce_session=1`,
    ),
  );
  assert.equal(response.status, 409);
  assert.deepEqual(setCookies(response), []);
});

test("a switch with no access cookie to bind to is refused", async () => {
  const response = await POST(store({ access_token: jwtFor("user-x"), expires_in: 900 }, "osce_rt=r"));
  assert.equal(response.status, 409);
  assert.deepEqual(setCookies(response), []);
});

function raw(headers: Record<string, string>, body = JSON.stringify({ access_token: "a", refresh_token: "r", expires_in: 900 })): NextRequest {
  return new NextRequest("http://localhost:3100/api/session", { method: "POST", headers, body });
}

test("a pair posted as a form or text, as a cross-site page can, is refused and stores nothing", async () => {
  for (const type of ["text/plain", "application/x-www-form-urlencoded", "multipart/form-data"]) {
    const response = await POST(raw({ "content-type": type, host: "localhost:3100" }));
    assert.equal(response.status, 403, type);
    assert.deepEqual(setCookies(response), []);
  }
  assert.equal((await POST(raw({ host: "localhost:3100" }))).status, 403);
});

test("a pair from another origin is refused, from this origin or with no Origin it is stored", async () => {
  const json = { "content-type": "application/json", host: "localhost:3100" };
  const foreign = await POST(raw({ ...json, origin: "https://evil.example" }));
  assert.equal(foreign.status, 403);
  assert.deepEqual(setCookies(foreign), []);
  assert.equal((await POST(raw({ ...json, origin: "null" }))).status, 403);
  assert.equal((await POST(raw({ ...json, origin: "http://localhost:3100" }))).status, 204);
  assert.equal((await POST(raw(json))).status, 204);
});

test("sign-out still works with no body and no content type", async () => {
  const response = await DELETE(new NextRequest("http://localhost:3100/api/session", { method: "DELETE" }));
  assert.equal(response.status, 204);
});
