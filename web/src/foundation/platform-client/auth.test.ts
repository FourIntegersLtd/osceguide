import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";

import {
  changePassword,
  logout,
  PasswordChangedNotStored,
  clearPlatformSession,
  register,
  exchangeLegacyToken,
  hasStoredSession,
  login,
  verifyMfaChallenge,
  peekPlatformAccessToken,
  platformAccessToken,
} from "@/foundation/platform-client/auth";
import { PlatformTransportError } from "@/foundation/platform-client/errors";
import { SESSION_MARKER_COOKIE } from "@/foundation/platform-client/sessionCookies";

const realFetch = globalThis.fetch;

/**
 * A cookie jar, because the session marker is read off `document.cookie`.
 *
 * Only the marker is ever written from this side — the tokens are set by the
 * route handlers as `httpOnly`, which is the whole point — so this jar stands
 * in for the readable half and the assertions below check that nothing else
 * ever lands in it.
 */
let jar = new Map<string, string>();

function installDocument(): void {
  jar = new Map();
  Object.defineProperty(globalThis, "document", {
    configurable: true,
    get: () => ({
      get cookie() {
        return [...jar].map(([k, v]) => `${k}=${v}`).join("; ");
      },
      set cookie(value: string) {
        const parts = value.split(";").map((part) => part.trim());
        const pair = parts[0] ?? "";
        const attrs = parts.slice(1);
        const index = pair.indexOf("=");
        const name = pair.slice(0, index);
        if (attrs.some((a) => a.toLowerCase() === "max-age=0")) jar.delete(name);
        else jar.set(name, pair.slice(index + 1));
      },
    }),
  });
}

/** What the server does when it writes the session cookies. */
function serverSetsMarker(): void {
  jar.set(SESSION_MARKER_COOKIE, "1");
}

interface Call {
  url: string;
  method: string;
}

function respond(handler: (call: Call) => Response): () => Call[] {
  const calls: Call[] = [];
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    const call = { url: String(input), method: init?.method ?? "GET" };
    calls.push(call);
    return handler(call);
  }) as typeof fetch;
  return () => calls;
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const PAIR = {
  status: "signed_in",
  access_token: "access-1",
  refresh_token: "refresh-1",
  token_type: "bearer",
  expires_in: 900,
  user: { id: "u1", email: "a@b.c" },
};

/** The platform answers the exchange; this app's server stores the pair. */
function exchangeThenStore(): () => Call[] {
  return respond((call) => {
    if (call.url.includes("/api/session")) {
      serverSetsMarker();
      return new Response(null, { status: 204 });
    }
    return json(PAIR);
  });
}

beforeEach(() => {
  installDocument();
  clearPlatformSession();
  jar.clear();
});

afterEach(() => {
  globalThis.fetch = realFetch;
  jar.clear();
  Reflect.deleteProperty(globalThis, "document");
});

test("a legacy token is traded for a platform pair and stored server-side", async () => {
  exchangeThenStore();
  const result = await exchangeLegacyToken("institution", "legacy-token");
  assert.equal(result?.access_token, "access-1");
  assert.equal(await platformAccessToken(), "access-1");
});

test("no token ever reaches anything a script can read", async () => {
  // The point of the whole arrangement: an XSS that reads every cookie it can
  // see finds a flag, not a thirty-day renewable session.
  exchangeThenStore();
  await exchangeLegacyToken("institution", "legacy-token");

  const readable = [...jar.entries()];
  assert.deepEqual(readable, [[SESSION_MARKER_COOKIE, "1"]]);
  assert.ok(!JSON.stringify(readable).includes("refresh-1"), "no refresh token on this side");
});

test("an address the migration has not reached yet is not an error", async () => {
  // It means "stay on the legacy backend", not "sign out of it", so the
  // caller gets null rather than an exception it would have to special-case.
  respond(() => json({ code: "legacy_account_not_imported", message: "not yet" }, 401));
  assert.equal(await exchangeLegacyToken("consumer", "legacy-token"), null);
});

test("any other refusal is raised, because it means something is wrong", async () => {
  respond(() => json({ code: "invalid_legacy_token", message: "no" }, 401));
  await assert.rejects(() => exchangeLegacyToken("consumer", "bad"));
});

test("concurrent callers share one request", async () => {
  // Refresh tokens are single-use with reuse detection: two refreshes racing
  // would revoke the whole chain and sign the person out. The console fires
  // several requests at once, so this is the normal case, not an edge one.
  serverSetsMarker();
  const calls = respond(() => json({ access_token: "access-2", expires_at: Date.now() + 900_000 }));

  const [a, b, c] = await Promise.all([
    platformAccessToken(),
    platformAccessToken(),
    platformAccessToken(),
  ]);
  assert.deepEqual([a, b, c], ["access-2", "access-2", "access-2"]);
  assert.equal(calls().length, 1, "three callers, one request");
});

test("a reload asks the server once and spends no refresh token", async () => {
  /*
   * This is the bug that signed people out on every reload. Module scope is
   * gone after a reload but the cookies are not, and the server answers from
   * the stored access token while it is still good — so the single-use
   * refresh token is not spent, and a second tab doing the same thing does
   * not read as theft.
   */
  serverSetsMarker();
  const calls = respond(() =>
    json({ access_token: "access-from-cookie", expires_at: Date.now() + 900_000 }),
  );

  assert.equal(await platformAccessToken(), "access-from-cookie");
  assert.equal(await platformAccessToken(), "access-from-cookie");
  assert.equal(calls().length, 1, "the second read comes from memory");
});

test("a refresh that answers after sign-out does not bring the session back", async () => {
  serverSetsMarker();
  let release: (response: Response) => void = () => {};
  const held = new Promise<Response>((resolve) => {
    release = resolve;
  });
  globalThis.fetch = (async (_input: RequestInfo | URL, init?: RequestInit) =>
    init?.method === "DELETE" ? new Response(null, { status: 204 }) : held) as typeof fetch;

  const refresh = platformAccessToken();
  await logout();
  release(json({ access_token: "late", expires_at: Date.now() + 900_000 }));

  assert.equal(await refresh, null);
  assert.equal(peekPlatformAccessToken(), null);
});

/** A token route answer the test releases by hand, so sign-out and sign-in can happen first. */
function holdRefresh(): (response: Response) => void {
  let release: (response: Response) => void = () => {};
  const held = new Promise<Response>((resolve) => {
    release = resolve;
  });
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (init?.method === "DELETE") return new Response(null, { status: 204 });
    if (url.endsWith("/api/session") && init?.method === "POST") {
      serverSetsMarker();
      return new Response(null, { status: 204 });
    }
    if (url.includes("/auth/login")) return json(PAIR);
    return held;
  }) as typeof fetch;
  return release;
}

test("a stale refresh refused after a new sign-in leaves the new session alone", async () => {
  serverSetsMarker();
  const release = holdRefresh();
  const stale = platformAccessToken();
  await logout();
  await login("a@b.c", "right-password");
  release(json({ access_token: null }));
  await stale;
  assert.equal(peekPlatformAccessToken(), "access-1");
  assert.equal(hasStoredSession(), true);
});

test("callers that joined a refresh across a sign-out and sign-in get the new session's token", async () => {
  serverSetsMarker();
  const release = holdRefresh();
  const stale = platformAccessToken();
  await logout();
  await login("a@b.c", "right-password");
  release(json({ access_token: "late", expires_at: Date.now() + 900_000 }));
  assert.equal(await stale, "access-1");
});

test("no session means no request at all", async () => {
  const calls = respond(() => json({ access_token: null }));
  assert.equal(await platformAccessToken(), null);
  assert.equal(calls().length, 0, "an anonymous page does not ask");
});

test("a spent chain signs the person out rather than retrying", async () => {
  serverSetsMarker();
  // The route handler clears the cookies itself and answers with no token.
  respond(() => {
    jar.delete(SESSION_MARKER_COOKIE);
    return json({ access_token: null });
  });

  assert.equal(await platformAccessToken(), null);
  assert.equal(hasStoredSession(), false);
});

test("an unreachable server is not a sign-out", async () => {
  // Offline, or this app's own server restarting. The cookies are untouched
  // and the caller can try again; dropping the session would be a blip
  // turning into a support ticket.
  serverSetsMarker();
  respond(() => json({ code: "transport_error", message: "no" }, 503));

  await assert.rejects(platformAccessToken(), PlatformTransportError);
  assert.equal(hasStoredSession(), true, "the session is still there");
});

test("the synchronous peek never makes a request", async () => {
  // It exists for `pagehide`, which has no time to await anything.
  exchangeThenStore();
  await exchangeLegacyToken("institution", "legacy-token");
  respond(() => {
    throw new Error("peek must not make a request");
  });
  assert.equal(peekPlatformAccessToken(), "access-1");
});

const CHALLENGE = { status: "mfa_required", challenge_token: "challenge-1", expires_in: 300 };

test("a sign-in that owes a second factor stores nothing", async () => {
  const calls = respond(() => json(CHALLENGE));
  const result = await login("a@b.c", "right-password");
  assert.equal(result.status, "mfa_required");
  // Storing the challenge as a session is what used to refuse these accounts.
  assert.equal(calls().some((call) => call.url.includes("/api/session")), false);
  assert.equal(hasStoredSession(), false);
});

test("the second factor finishes the sign-in and stores the pair", async () => {
  const calls = exchangeThenStore();
  const result = await verifyMfaChallenge("challenge-1", { code: "123456" });
  assert.equal(result.access_token, "access-1");
  assert.ok(calls().some((call) => call.url.endsWith("/api/v1/auth/mfa/verify")));
  assert.equal(await platformAccessToken(), "access-1");
});

test("a legacy exchange that needs a second factor stays on the old session", async () => {
  const calls = respond(() => json(CHALLENGE));
  assert.equal(await exchangeLegacyToken("institution", "legacy-token"), null);
  assert.equal(calls().some((call) => call.url.includes("/api/session")), false);
});

test("an account created but not stored says to sign in, not to try again", async () => {
  respond((call) => {
    if (call.url.includes("/api/session")) return new Response(null, { status: 500 });
    return json({ ...PAIR, status: "signed_in" }, 201);
  });
  await assert.rejects(register({ email: "new@example.com", password: "correct horse", name: "New" }), {
    name: "AccountCreatedNotSignedIn",
    message:
      "Your account was created, but we couldn't sign you in. Sign in with the email and password you just chose.",
  });
});

test("changing the password adopts the fresh pair, so this tab stays signed in", async () => {
  const calls = respond((call) => {
    if (call.url.includes("/api/session/token")) return json({ access_token: "access-1", expires_at: Date.now() + 900_000 });
    if (call.url.includes("/api/session")) {
      serverSetsMarker();
      return new Response(null, { status: 204 });
    }
    return json({ access_token: "access-2", refresh_token: "refresh-2", token_type: "bearer", expires_in: 900 });
  });
  await changePassword("old password", "new password here");
  assert.ok(calls().some((call) => call.url.endsWith("/api/v1/auth/change-password")));
  assert.ok(calls().some((call) => call.method === "POST" && call.url.endsWith("/api/session")));
  assert.equal(await platformAccessToken(), "access-2");
});

test("a password changed but not stored says the change happened and to sign in with it", async () => {
  respond((call) => {
    if (call.url.includes("/api/session")) return new Response(null, { status: 500 });
    return json({ access_token: "access-2", refresh_token: "refresh-2", token_type: "bearer", expires_in: 900 });
  });
  await assert.rejects(changePassword("old password", "new password here"), (error: unknown) => {
    assert.ok(error instanceof PasswordChangedNotStored);
    assert.equal(
      error.message,
      "Your password was changed, but we couldn't keep you signed in. Sign in with your new password.",
    );
    return true;
  });
});
