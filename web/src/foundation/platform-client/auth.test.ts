import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";

import {
  STORAGE_KEYS,
  clearPlatformSession,
  exchangeLegacyToken,
  peekPlatformAccessToken,
  platformAccessToken,
} from "@/foundation/platform-client/auth";

const realFetch = globalThis.fetch;

/** `localStorage` does not exist under `node --test`. */
function installStorage(): void {
  const store = new Map<string, string>();
  (globalThis as { window?: unknown }).window = {
    localStorage: {
      getItem: (k: string) => store.get(k) ?? null,
      setItem: (k: string, v: string) => void store.set(k, v),
      removeItem: (k: string) => void store.delete(k),
    },
  };
}

function respondWith(status: number, body: unknown): () => number {
  let calls = 0;
  globalThis.fetch = (async () => {
    calls += 1;
    return new Response(JSON.stringify(body), {
      status,
      headers: { "content-type": "application/json" },
    });
  }) as typeof fetch;
  return () => calls;
}

const PAIR = {
  access_token: "access-1",
  refresh_token: "refresh-1",
  token_type: "bearer",
  expires_in: 900,
  user: { id: "u1", email: "a@b.c" },
};

beforeEach(() => {
  installStorage();
  clearPlatformSession();
});

afterEach(() => {
  globalThis.fetch = realFetch;
  clearPlatformSession();
  delete (globalThis as { window?: unknown }).window;
});

test("a legacy token is traded for a platform pair and remembered", async () => {
  respondWith(200, PAIR);
  const result = await exchangeLegacyToken("institution", "legacy-token");
  assert.equal(result?.access_token, "access-1");
  assert.equal(await platformAccessToken(), "access-1");
  assert.equal(window.localStorage.getItem(STORAGE_KEYS.refresh), "refresh-1");
});

test("an address the migration has not reached yet is not an error", async () => {
  // It means "stay on the legacy backend", not "sign out of it", so the
  // caller gets null rather than an exception it would have to special-case.
  respondWith(401, { code: "legacy_account_not_imported", message: "not yet" });
  assert.equal(await exchangeLegacyToken("consumer", "legacy-token"), null);
});

test("any other refusal is raised, because it means something is wrong", async () => {
  respondWith(401, { code: "invalid_legacy_token", message: "no" });
  await assert.rejects(() => exchangeLegacyToken("consumer", "bad"));
});

test("concurrent callers share one refresh", async () => {
  // Refresh tokens are single-use with reuse detection: two refreshes racing
  // would revoke the whole chain and sign the person out. The console fires
  // several requests at once, so this is the normal case, not an edge one.
  respondWith(200, PAIR);
  await exchangeLegacyToken("institution", "legacy-token");

  window.localStorage.setItem(STORAGE_KEYS.access, "stale");
  clearPlatformSession();
  window.localStorage.setItem(STORAGE_KEYS.access, "stale");
  window.localStorage.setItem(STORAGE_KEYS.refresh, "refresh-1");

  const calls = respondWith(200, { ...PAIR, access_token: "access-2" });
  const [a, b, c] = await Promise.all([
    platformAccessToken(),
    platformAccessToken(),
    platformAccessToken(),
  ]);
  assert.deepEqual([a, b, c], ["access-2", "access-2", "access-2"]);
  assert.equal(calls(), 1, "three callers, one refresh");
});

test("a refused refresh drops the session rather than retrying a dead chain", async () => {
  window.localStorage.setItem(STORAGE_KEYS.access, "stale");
  window.localStorage.setItem(STORAGE_KEYS.refresh, "spent");
  respondWith(401, { code: "invalid_refresh_token", message: "gone" });

  assert.equal(await platformAccessToken(), null);
  assert.equal(window.localStorage.getItem(STORAGE_KEYS.refresh), null);
});

test("the synchronous peek never refreshes", async () => {
  // It exists for `pagehide`, which has no time to await anything.
  respondWith(200, PAIR);
  await exchangeLegacyToken("institution", "legacy-token");
  globalThis.fetch = (async () => {
    throw new Error("peek must not make a request");
  }) as typeof fetch;
  assert.equal(peekPlatformAccessToken(), "access-1");
});

test("a reload does not spend the refresh token when the access token is still good", async () => {
  /*
   * This is the bug that signed people out on every reload.
   *
   * Refresh tokens are single-use with reuse detection. The expiry used not to
   * be stored, so a restored session was always treated as due and every page
   * load refreshed — and two module instances doing that at once (a
   * code-split chunk, a second tab) spent the same token twice, which reads as
   * theft and revokes the whole chain.
   */
  respondWith(200, PAIR);
  await exchangeLegacyToken("institution", "legacy-token");

  // A fresh page load: module scope is gone, storage is not.
  clearPlatformSessionMemoryOnly();

  const calls = respondWith(500, { code: "should_not_be_called", message: "" });
  assert.equal(await platformAccessToken(), "access-1");
  assert.equal(calls(), 0, "a valid access token needs no refresh");
});

test("a reload refreshes once the stored expiry has passed", async () => {
  respondWith(200, PAIR);
  await exchangeLegacyToken("institution", "legacy-token");
  window.localStorage.setItem(STORAGE_KEYS.expiresAt, String(Date.now() - 1));
  clearPlatformSessionMemoryOnly();

  const calls = respondWith(200, { ...PAIR, access_token: "access-2", refresh_token: "refresh-2" });
  assert.equal(await platformAccessToken(), "access-2");
  assert.equal(calls(), 1);
});

test("losing a refresh race adopts the winner's pair rather than signing out", async () => {
  // Two module instances can refresh at once — a second tab, or a code-split
  // chunk with its own scope. The loser's token is spent through no fault of
  // the person using it, and their session is alive in storage.
  window.localStorage.setItem(STORAGE_KEYS.access, "stale");
  window.localStorage.setItem(STORAGE_KEYS.refresh, "mine");

  globalThis.fetch = (async () => {
    // Meanwhile the other instance finished and stored its pair.
    window.localStorage.setItem(STORAGE_KEYS.access, "access-from-winner");
    window.localStorage.setItem(STORAGE_KEYS.refresh, "refresh-from-winner");
    window.localStorage.setItem(STORAGE_KEYS.expiresAt, String(Date.now() + 900_000));
    return new Response(JSON.stringify({ code: "invalid_refresh_token", message: "spent" }), {
      status: 401,
      headers: { "content-type": "application/json" },
    });
  }) as typeof fetch;

  assert.equal(await platformAccessToken(), "access-from-winner");
  assert.equal(window.localStorage.getItem(STORAGE_KEYS.refresh), "refresh-from-winner");
});

/** Drop the in-memory session, keeping storage: what a page reload does. */
function clearPlatformSessionMemoryOnly(): void {
  const keep = {
    access: window.localStorage.getItem(STORAGE_KEYS.access),
    refresh: window.localStorage.getItem(STORAGE_KEYS.refresh),
    expiresAt: window.localStorage.getItem(STORAGE_KEYS.expiresAt),
  };
  clearPlatformSession();
  if (keep.access) window.localStorage.setItem(STORAGE_KEYS.access, keep.access);
  if (keep.refresh) window.localStorage.setItem(STORAGE_KEYS.refresh, keep.refresh);
  if (keep.expiresAt) window.localStorage.setItem(STORAGE_KEYS.expiresAt, keep.expiresAt);
}
