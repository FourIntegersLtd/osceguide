import { platformRequest, setPlatformTokenSource } from "@/foundation/platform-client/client";
import { hasCode } from "@/foundation/platform-client/errors";
import type { components } from "@/foundation/platform-client/schema";

/**
 * The platform session: tokens in, tokens refreshed, tokens forgotten.
 *
 * `platform-api` owns identity for every product, so there is one login and
 * one pair of tokens whether the person is a consumer, an institution
 * supervisor or an employer reviewer. Which surface they land on is decided by
 * their memberships, not by which login page they used.
 *
 * `exchangeLegacyToken` is kept for the cutover: no password came across from
 * the old backends (one hashed with bcrypt, the other with unsalted SHA-256),
 * so an imported person trades the token their old session already holds for a
 * platform pair. It goes when the legacy backends do.
 */

type AuthResult = components["schemas"]["AuthResult"];

/** Which retiring backend the caller's current session came from. */
export type LegacyProvider = "consumer" | "institution";

const ACCESS_KEY = "osce_platform_access_token";
const REFRESH_KEY = "osce_platform_refresh_token";
/**
 * Refresh this long before the access token expires.
 *
 * Tokens live fifteen minutes. Refreshing a minute early costs one extra
 * request an hour and avoids the race where a token passes the check here and
 * expires in flight.
 */
const REFRESH_MARGIN_MS = 60_000;

interface StoredSession {
  accessToken: string;
  refreshToken: string;
  /** Epoch milliseconds. */
  expiresAt: number;
}

let session: StoredSession | null = null;
let inFlight: Promise<string | null> | null = null;

function read(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    // Safari in private mode throws on access rather than returning null.
    return null;
  }
}

function write(key: string, value: string | null): void {
  try {
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
  } catch {
    // Storage being unavailable makes the session last one page view, which
    // is worse than persisting it and better than failing to sign in.
  }
}

function remember(result: AuthResult): StoredSession {
  const stored: StoredSession = {
    accessToken: result.access_token,
    refreshToken: result.refresh_token,
    expiresAt: Date.now() + result.expires_in * 1000,
  };
  session = stored;
  write(ACCESS_KEY, stored.accessToken);
  write(REFRESH_KEY, stored.refreshToken);
  return stored;
}

/**
 * Adopt a pair the platform just issued.
 *
 * Switching workspace re-mints the token with a different active membership,
 * so the new one has to replace the stored one or every later request still
 * claims the old workspace.
 */
export function rememberPlatformSession(result: AuthResult): void {
  remember(result);
}

/** Forget the platform session. The legacy one is untouched. */
export function clearPlatformSession(): void {
  session = null;
  inFlight = null;
  write(ACCESS_KEY, null);
  write(REFRESH_KEY, null);
}

/**
 * Trade a legacy token for a platform one.
 *
 * `legacy_account_not_imported` is not an error to shout about: it means this
 * person's records have not been migrated yet, and the right response is to
 * leave them on the old backend rather than to sign them out of it. The
 * caller gets `null` and everything stays where it was.
 */
export async function exchangeLegacyToken(
  provider: LegacyProvider,
  token: string,
): Promise<AuthResult | null> {
  try {
    const result = await platformRequest<AuthResult>("/api/v1/auth/exchange-legacy", {
      method: "POST",
      body: { provider, token },
    });
    remember(result);
    return result;
  } catch (error) {
    if (hasCode(error, "legacy_account_not_imported")) return null;
    throw error;
  }
}

async function refresh(): Promise<string | null> {
  const refreshToken = session?.refreshToken ?? read(REFRESH_KEY);
  if (!refreshToken) return null;
  try {
    const pair = await platformRequest<AuthResult>("/api/v1/auth/refresh", {
      method: "POST",
      body: { refresh_token: refreshToken },
    });
    return remember(pair).accessToken;
  } catch {
    // A refused refresh means the chain is spent or revoked. Dropping it
    // sends the next call back through the exchange rather than retrying a
    // token that will never work again.
    clearPlatformSession();
    return null;
  }
}

/**
 * The access token, refreshed if it is about to expire.
 *
 * Concurrent callers share one refresh: the console fires several requests at
 * once, and refresh tokens are single-use with reuse detection, so two
 * refreshes racing would revoke the whole chain and sign the person out.
 */
export async function platformAccessToken(): Promise<string | null> {
  if (!session) {
    const accessToken = read(ACCESS_KEY);
    const refreshToken = read(REFRESH_KEY);
    if (!accessToken || !refreshToken) return null;
    // The expiry is not stored, so a token restored from a previous page load
    // is treated as due: one refresh is cheaper than one 401.
    session = { accessToken, refreshToken, expiresAt: 0 };
  }
  if (Date.now() < session.expiresAt - REFRESH_MARGIN_MS) return session.accessToken;
  inFlight ??= refresh().finally(() => {
    inFlight = null;
  });
  return inFlight;
}

/**
 * Install the token source. Call once, where the app starts.
 *
 * Separate from the module body so importing this file has no side effect —
 * a module-level call would run during a Next.js server render, where there
 * is no `window`.
 */
export function installPlatformAuth(): void {
  setPlatformTokenSource(platformAccessToken);
}

/**
 * The stored access token, without refreshing it.
 *
 * For the one caller that cannot await: a `pagehide` handler has no time to
 * refresh, and the alternative — `sendBeacon`, which cannot set headers at
 * all — sends the request unauthenticated. A slightly stale token that the
 * backend refuses loses one batch; no token loses every batch sent on the way
 * out of the page, which is most of them.
 */
export function peekPlatformAccessToken(): string | null {
  return session?.accessToken ?? read(ACCESS_KEY);
}

/** Exported for the tests, which need to start from nothing. */
export const STORAGE_KEYS = { access: ACCESS_KEY, refresh: REFRESH_KEY } as const;


/** Sign in. One login for every product. */
export async function login(email: string, password: string): Promise<AuthResult> {
  const result = await platformRequest<AuthResult>("/api/v1/auth/login", {
    method: "POST",
    body: { email, password },
  });
  remember(result);
  return result;
}

/** Create a consumer account. Institutions provision their people instead. */
export async function register(input: {
  email: string;
  password: string;
  name: string;
}): Promise<AuthResult> {
  const result = await platformRequest<AuthResult>("/api/v1/auth/register", {
    method: "POST",
    body: input,
  });
  remember(result);
  return result;
}

/**
 * Sign out.
 *
 * The refresh token is revoked server-side first, because clearing local
 * storage alone leaves a working token in the hands of whoever has the device.
 * A failed revoke still clears locally: the person asked to be signed out.
 */
export async function logout(): Promise<void> {
  const refreshToken = session?.refreshToken ?? read(REFRESH_KEY);
  try {
    if (refreshToken) {
      await platformRequest<void>("/api/v1/auth/logout", {
        method: "POST",
        body: { refresh_token: refreshToken },
      });
    }
  } catch {
    // Revoking is best effort; the local session goes regardless.
  } finally {
    clearPlatformSession();
  }
}

/** Move to another workspace, re-minting the token with it active. */
export async function switchWorkspace(orgSlug: string): Promise<AuthResult> {
  const result = await platformRequest<AuthResult>("/api/v1/auth/switch-workspace", {
    method: "POST",
    body: { org_slug: orgSlug },
  });
  // The new token *is* the switch; keeping the old one would leave every later
  // request claiming the workspace the person just left.
  remember(result);
  return result;
}

export async function changePassword(current: string, next: string): Promise<void> {
  await platformRequest<void>("/api/v1/auth/change-password", {
    method: "POST",
    body: { current_password: current, new_password: next },
  });
}

export async function requestPasswordReset(email: string): Promise<void> {
  await platformRequest<void>("/api/v1/auth/password-reset", {
    method: "POST",
    body: { email },
  });
}

export function hasStoredSession(): boolean {
  return Boolean(session?.accessToken ?? read(ACCESS_KEY));
}

/**
 * A short-lived ticket for an EventSource.
 *
 * `EventSource` cannot set an Authorization header, so the backend accepts a
 * one-shot ticket in the query string instead. It is minted per connection and
 * expires in seconds, which is why it is safe to put somewhere a URL might be
 * logged — unlike the access token.
 */
export async function mintStreamTicket(): Promise<string> {
  const { ticket } = await platformRequest<{ ticket: string; expires_in: number }>(
    "/api/v1/auth/stream-ticket",
    { method: "POST" },
  );
  return ticket;
}
