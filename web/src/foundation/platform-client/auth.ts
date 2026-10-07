import { platformRequest, setPlatformTokenSource } from "@/foundation/platform-client/client";
import { hasCode, isPlatformError } from "@/foundation/platform-client/errors";
import { noteOrgRefusal } from "@/foundation/platform-client/orgSuspension";
import {
  REFRESH_MARGIN_MS,
  SESSION_MARKER_COOKIE,
} from "@/foundation/platform-client/sessionCookies";
import type { components } from "@/foundation/platform-client/schema";

/**
 * The platform session: tokens in, tokens refreshed, tokens forgotten.
 *
 * `platform-api` owns identity for every product, so there is one login and
 * one pair of tokens whether the person is a consumer, an institution
 * supervisor or an employer reviewer. Which surface they land on is decided by
 * their memberships, not by which login page they used.
 *
 * **Where the tokens live.** The refresh token is not here and never is: it
 * goes straight into an `httpOnly` cookie owned by this app's own route
 * handlers under `/api/session`, and only the Next server ever spends it. This
 * module holds one access token in memory, for fifteen minutes at a time. The
 * reasoning is in `sessionCookies.ts`; the short version is that `localStorage`
 * is readable by any script on the page, so one XSS used to be worth a
 * thirty-day renewable session rather than a fifteen-minute one.
 *
 * `exchangeLegacyToken` is kept for the cutover: no password came across from
 * the old backends (one hashed with bcrypt, the other with unsalted SHA-256),
 * so an imported person trades the token their old session already holds for a
 * platform pair. It goes when the legacy backends do.
 */

type AuthResult = components["schemas"]["AuthResult"];
type MfaEnrolmentStart = components["schemas"]["MfaEnrolmentStart"];
type MfaEnrolmentConfirmed = components["schemas"]["MfaEnrolmentConfirmed"];

/**
 * What a password sign-in answers: a session, or a second step.
 *
 * `mfa_required` means an authenticator is set up and a code is owed;
 * `mfa_enrolment_required` means policy demands one and none is set up yet.
 * Both carry a short-lived `challenge_token` that only the `/auth/mfa/*`
 * routes accept. Nothing is stored until the answer is `signed_in`: storing a
 * challenge as a session is how a person with a second factor used to be
 * refused with "Could not store the session".
 */
export type SignInResult =
  | AuthResult
  | components["schemas"]["MfaRequiredResponse"]
  | components["schemas"]["MfaEnrolmentRequiredResponse"];

export type MfaChallenge = Exclude<SignInResult, AuthResult>;

/** Which retiring backend the caller's current session came from. */
export type LegacyProvider = "consumer" | "institution";

/** This app's own session endpoints, not platform-api's. */
const SESSION_ENDPOINT = "/api/session";
const TOKEN_ENDPOINT = "/api/session/token";

interface CachedToken {
  accessToken: string;
  /** Epoch milliseconds. */
  expiresAt: number;
}

let session: CachedToken | null = null;
let inFlight: Promise<string | null> | null = null;

/* ---------- the session marker ---------- */

/**
 * Whether a session exists, answered synchronously and without a secret.
 *
 * `SessionProvider` decides whether to bother trying before it can await
 * anything, and it cannot read an `httpOnly` cookie. The server sets a
 * separate readable cookie carrying this one bit.
 */
function hasMarker(): boolean {
  if (typeof document === "undefined") return false;
  return document.cookie
    .split(";")
    .some((entry) => entry.trim().startsWith(`${SESSION_MARKER_COOKIE}=`));
}

function dropMarker(): void {
  if (typeof document === "undefined") return;
  document.cookie = `${SESSION_MARKER_COOKIE}=; path=/; max-age=0`;
}

/* ---------- storing and forgetting ---------- */

/** Drop what this tab holds. The server's cookies are cleared separately. */
function forgetLocally(): void {
  session = null;
  inFlight = null;
  dropMarker();
}

async function remember(
  result: Pick<AuthResult, "access_token" | "refresh_token" | "expires_in">,
): Promise<void> {
  const response = await fetch(SESSION_ENDPOINT, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({
      access_token: result.access_token,
      refresh_token: result.refresh_token,
      expires_in: result.expires_in,
    }),
  });
  if (!response.ok) {
    // Without the cookie there is no session to come back to on the next page
    // load, so failing loudly beats appearing to sign in and then not having.
    throw new Error("Could not store the session");
  }
  session = {
    accessToken: result.access_token,
    expiresAt: Date.now() + result.expires_in * 1000,
  };
}

/**
 * Adopt a pair the platform just issued.
 *
 * Switching workspace re-mints the token with a different active membership,
 * so the new one has to replace the stored one or every later request still
 * claims the old workspace.
 *
 * Typed as the pair rather than as `AuthResult`, because not every issuer of a
 * pair also returns a profile: `POST /auth/sso/callback` answers `SsoSession`,
 * which is a token pair and nothing else — the person is read afterwards from
 * `GET /me`, which is where the profile lives anyway. Widening the parameter is
 * what lets that caller be honest instead of casting a `user` into existence.
 *
 * Awaitable now that storing is a request to this app's own server. Callers
 * that do not await it will navigate before the cookie is set.
 */
export async function rememberPlatformSession(
  result: Pick<AuthResult, "access_token" | "refresh_token" | "expires_in">,
): Promise<void> {
  await remember(result);
}

/**
 * Forget the platform session. The legacy one is untouched.
 *
 * Synchronous for its callers, so the marker goes at once and nothing decides
 * a person is still signed in while the request is in flight. The cookies
 * themselves are dropped by the server; `logout` awaits that, this does not.
 */
export function clearPlatformSession(): void {
  forgetLocally();
  if (typeof fetch === "undefined") return;
  void fetch(SESSION_ENDPOINT, { method: "DELETE", credentials: "same-origin" }).catch(() => {
    // The cookies outlive this tab if the request never lands. The tokens in
    // them are still subject to their own expiry, and the next sign-in
    // replaces them.
  });
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
    const result = await platformRequest<SignInResult>("/api/v1/auth/exchange-legacy", {
      method: "POST",
      body: { provider, token },
    });
    // A second factor cannot be asked for in the middle of a silent exchange,
    // so an account that needs one stays on the old session and signs in here
    // through the form, which can.
    if (result.status !== "signed_in") return null;
    await remember(result);
    return result;
  } catch (error) {
    if (hasCode(error, "legacy_account_not_imported")) return null;
    throw error;
  }
}

/* ---------- reading the token ---------- */

/**
 * Hold a named lock across every tab on this origin, if the browser has them.
 *
 * Refresh tokens are single-use with reuse detection, and all this browser's
 * tabs share one cookie — so two tabs refreshing at the same moment would
 * spend the same token twice and revoke the whole chain. Serialising them here
 * means the second tab arrives after the first has already stored a new pair,
 * and the server then answers it from the cookie without refreshing at all.
 *
 * Different browsers and devices hold different cookies, so there is no race
 * to lose between them.
 */
async function withSessionLock<T>(run: () => Promise<T>): Promise<T> {
  const locks = typeof navigator !== "undefined" ? navigator.locks : undefined;
  if (!locks) return run();
  return locks.request("osce-platform-session", run);
}

async function fetchToken(): Promise<string | null> {
  return withSessionLock(async () => {
    let response: Response;
    try {
      response = await fetch(TOKEN_ENDPOINT, {
        method: "POST",
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      });
    } catch {
      // Offline, or this app's own server is down. Not a reason to sign
      // anybody out; the caller can try again.
      return null;
    }
    if (!response.ok) return null;

    const body = (await response.json()) as { access_token: string | null; expires_at?: number };
    if (!body.access_token) {
      // The server has already cleared the cookies: the chain was spent or
      // revoked, or there was never a session here.
      forgetLocally();
      return null;
    }
    session = {
      accessToken: body.access_token,
      expiresAt: body.expires_at ?? Date.now() + REFRESH_MARGIN_MS,
    };
    return session.accessToken;
  });
}

/**
 * The access token, refreshed if it is about to expire.
 *
 * Concurrent callers in this tab share one request, and `withSessionLock`
 * covers the other tabs.
 */
export async function platformAccessToken(): Promise<string | null> {
  if (session && Date.now() < session.expiresAt - REFRESH_MARGIN_MS) return session.accessToken;
  // No marker means no session at all, and asking would be a pointless round
  // trip on every anonymous page.
  if (!session && !hasMarker()) return null;
  inFlight ??= fetchToken().finally(() => {
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
 * The cached access token, without refreshing it.
 *
 * For the one caller that cannot await: a `pagehide` handler has no time to
 * refresh, and the alternative — `sendBeacon`, which cannot set headers at
 * all — sends the request unauthenticated.
 *
 * It answers from memory only, because the stored token is in an `httpOnly`
 * cookie this side cannot read. So a page that is closed before anything
 * asked for a token sends its last batch unauthenticated and loses it. That
 * is the price of the refresh token being out of reach, and it is one batch
 * on the way out of a page rather than a session in somebody else's hands.
 */
export function peekPlatformAccessToken(): string | null {
  return session?.accessToken ?? null;
}

/* ---------- signing in and out ---------- */

/**
 * Sign in. One login for every product.
 *
 * Answers the session, or the second step the account owes (see
 * `SignInResult`). Only a finished sign-in is stored.
 */
export async function login(email: string, password: string): Promise<SignInResult> {
  const result = await platformRequest<SignInResult>("/api/v1/auth/login", {
    method: "POST",
    body: { email, password },
  });
  if (result.status === "signed_in") await remember(result);
  return result;
}

/**
 * Redeem a sign-in challenge with an authenticator code or a recovery code.
 *
 * Exactly one of the two is sent. A recovery code is spent by using it.
 */
export async function verifyMfaChallenge(
  challengeToken: string,
  answer: { code: string } | { recoveryCode: string },
): Promise<AuthResult> {
  const result = await platformRequest<AuthResult>("/api/v1/auth/mfa/verify", {
    method: "POST",
    body:
      "code" in answer
        ? { challenge_token: challengeToken, code: answer.code }
        : { challenge_token: challengeToken, recovery_code: answer.recoveryCode },
  });
  await remember(result);
  return result;
}

/** The secret to set up an authenticator with, when sign-in said one is required. */
export function startMfaEnrolmentAtSignIn(challengeToken: string): Promise<MfaEnrolmentStart> {
  return platformRequest<MfaEnrolmentStart>("/api/v1/auth/mfa/enrol/start", {
    method: "POST",
    body: { challenge_token: challengeToken },
  });
}

/**
 * Confirm that authenticator with its first code, and finish signing in.
 *
 * The answer carries the recovery codes, and this is the only time they are
 * ever sent: the caller must show them before moving on.
 */
export async function confirmMfaEnrolmentAtSignIn(
  challengeToken: string,
  code: string,
): Promise<MfaEnrolmentConfirmed> {
  const result = await platformRequest<MfaEnrolmentConfirmed>("/api/v1/auth/mfa/enrol/confirm", {
    method: "POST",
    body: { challenge_token: challengeToken, code },
  });
  await remember(result);
  return result;
}

/**
 * Create a consumer account. Institutions provision their people instead.
 *
 * `examCode` is which exam they came to sit. The retiring client got it from
 * the hostname — `sca.osceguide.com` — and on one domain the per-exam landing
 * pages carry it into this form instead. Optional, because somebody arriving
 * at the site root has not said yet.
 */
export async function register(input: {
  email: string;
  password: string;
  name: string;
  examCode?: string | null;
}): Promise<AuthResult> {
  const result = await platformRequest<SignInResult>("/api/v1/auth/register", {
    method: "POST",
    body: {
      email: input.email,
      password: input.password,
      name: input.name,
      exam_code: input.examCode || null,
    },
  });
  // A new consumer account belongs to no organisation that could require a
  // second factor. The route shares sign-in's answer shape, so say so rather
  // than store a challenge as a session.
  if (result.status !== "signed_in") {
    throw new Error("This account needs two-factor sign-in. Sign in to finish setting it up.");
  }
  await remember(result);
  return result;
}

/**
 * Sign out.
 *
 * The revoking moved to `DELETE /api/session`, which is the only side that
 * still holds the refresh token. It awaits the revoke rather than firing it
 * off, so a person who signs out and closes the tab is actually signed out.
 */
export async function logout(): Promise<void> {
  try {
    await fetch(SESSION_ENDPOINT, { method: "DELETE", credentials: "same-origin" });
  } catch {
    // Revoking is best effort; the local session goes regardless.
  } finally {
    forgetLocally();
  }
}

/**
 * Re-mint the token against another workspace.
 *
 * `null` is a person's own practice, which is a destination rather than an
 * absence: somebody in a cohort still has their own entitlements and their own
 * attempts. Without it, joining an institution was a one-way door.
 */
export async function switchWorkspace(orgSlug: string | null): Promise<AuthResult> {
  let result: AuthResult;
  try {
    result = await platformRequest<AuthResult>("/api/v1/auth/switch-workspace", {
      method: "POST",
      body: { org_slug: orgSlug },
    });
  } catch (error) {
    // The org is not in this path, so the suspension is noted by name.
    if (isPlatformError(error)) noteOrgRefusal("", error.code, orgSlug);
    throw error;
  }
  // The new token *is* the switch; keeping the old one would leave every later
  // request claiming the workspace the person just left.
  await remember(result);
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

/**
 * Finish a password reset.
 *
 * The token comes from the emailed link. A refused one is expired or already
 * spent, and the person has to ask for another — there is no way to tell those
 * two apart without telling an attacker which addresses have accounts.
 * Returns the account's email, so an accepted invitation can sign straight in.
 */
export async function confirmPasswordReset(token: string, newPassword: string): Promise<string> {
  const done = await platformRequest<{ email: string }>("/api/v1/auth/password-reset/confirm", {
    method: "POST",
    body: { token, password: newPassword },
  });
  return done.email;
}

export function hasStoredSession(): boolean {
  return Boolean(session?.accessToken) || hasMarker();
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
