import type { NextRequest, NextResponse } from "next/server";

/**
 * Where the platform session actually lives: `httpOnly` cookies on this app's
 * own origin, written by the route handlers under `/api/session`.
 *
 * The tokens used to sit in `localStorage`, which any script on the page can
 * read. That put the *refresh* token — thirty days, renewable, single-use with
 * reuse detection — within reach of a single XSS anywhere in the app, and this
 * app renders user-authored content (community posts, station comments, media
 * articles). Stealing it meant an indefinitely renewable session off-device,
 * and the fifteen-minute access token expiry bought nothing, because whoever
 * held the refresh token could mint another.
 *
 * So the refresh token never reaches the browser any more. It goes in an
 * `httpOnly` cookie that JavaScript cannot read, and only the Next server
 * spends it. XSS can still ask `/api/session/token` for an access token — that
 * is unavoidable while the browser talks to the API directly — but that token
 * expires in fifteen minutes and cannot be renewed. The blast radius is
 * contained rather than handed over.
 *
 * ADR 0004 ("platform-api sets no cookies") is untouched: platform-api still
 * issues bare token pairs and never knows a cookie exists. The cookie is this
 * app's, on this app's origin.
 */

/** The refresh token. Never leaves the server. */
const REFRESH_COOKIE = "osce_rt";
/** The current access token, so a reload does not have to spend the refresh. */
const ACCESS_COOKIE = "osce_at";
/** When the access token expires, epoch milliseconds. */
const EXPIRES_COOKIE = "osce_at_exp";
/**
 * "A session exists" — no secret in it, and deliberately readable by scripts.
 *
 * `SessionProvider` asks synchronously whether to bother trying, which it
 * cannot do against an `httpOnly` cookie. This carries that one bit and
 * nothing else.
 */
export const SESSION_MARKER_COOKIE = "osce_session";

export const SESSION_COOKIES = {
  refresh: REFRESH_COOKIE,
  access: ACCESS_COOKIE,
  expiresAt: EXPIRES_COOKIE,
  marker: SESSION_MARKER_COOKIE,
} as const;

/** Matches `jwt_refresh_ttl_seconds` in platform-api's settings. */
const REFRESH_TTL_SECONDS = 30 * 24 * 60 * 60;

/**
 * Refresh this long before the access token expires.
 *
 * Tokens live fifteen minutes. Refreshing a minute early costs one extra
 * request an hour and avoids the race where a token passes the check here and
 * expires in flight.
 */
export const REFRESH_MARGIN_MS = 60_000;

export interface TokenPair {
  accessToken: string;
  refreshToken: string;
  /** Epoch milliseconds. */
  expiresAt: number;
}

function secure(): boolean {
  // Local development is plain http, where a `Secure` cookie is dropped
  // silently and sign-in appears to succeed and then not have happened.
  return process.env.NODE_ENV === "production";
}

export function readSessionCookies(request: NextRequest): Partial<TokenPair> {
  const expiresAt = Number(request.cookies.get(EXPIRES_COOKIE)?.value);
  return {
    accessToken: request.cookies.get(ACCESS_COOKIE)?.value,
    refreshToken: request.cookies.get(REFRESH_COOKIE)?.value,
    expiresAt: Number.isFinite(expiresAt) ? expiresAt : undefined,
  };
}

function cookieOptions() {
  return {
    httpOnly: true,
    secure: secure(),
    // `Lax` rather than `Strict`: the SSO callback and the emailed reset and
    // join links are top-level navigations from another site, and `Strict`
    // would drop the cookie on exactly those arrivals. `Lax` still refuses
    // every cross-site subrequest, which is what CSRF actually needs.
    sameSite: "lax",
    path: "/",
    maxAge: REFRESH_TTL_SECONDS,
  } as const;
}

export function writeSessionCookies(response: NextResponse, pair: TokenPair): NextResponse {
  response.cookies.set(REFRESH_COOKIE, pair.refreshToken, cookieOptions());
  return writeAccessCookies(response, pair);
}

/**
 * Replace the access token only, for an issuer that continues the same refresh
 * chain (a workspace switch). The refresh cookie is not rewritten, so its
 * lifetime still ends where the server's chain ends.
 */
export function writeAccessCookies(
  response: NextResponse,
  pair: Pick<TokenPair, "accessToken" | "expiresAt">,
): NextResponse {
  const base = cookieOptions();
  response.cookies.set(ACCESS_COOKIE, pair.accessToken, base);
  response.cookies.set(EXPIRES_COOKIE, String(pair.expiresAt), base);
  // The marker is the one a script may read, so it carries no token.
  response.cookies.set(SESSION_MARKER_COOKIE, "1", { ...base, httpOnly: false });
  return response;
}

export function clearSessionCookies(response: NextResponse): NextResponse {
  for (const name of Object.values(SESSION_COOKIES)) {
    response.cookies.set(name, "", {
      httpOnly: name !== SESSION_MARKER_COOKIE,
      secure: secure(),
      sameSite: "lax",
      path: "/",
      maxAge: 0,
    });
  }
  return response;
}

/**
 * The claims of a token, read without verifying it. platform-api verifies every token it is
 * shown; callers here only pair two tokens or pass a hint back to it. `null` when unreadable.
 */
export function readTokenClaims(token: string | undefined): Record<string, unknown> | null {
  try {
    const payload = token?.split(".")[1];
    if (!payload) return null;
    const claims: unknown = JSON.parse(Buffer.from(payload, "base64url").toString("utf8"));
    return claims && typeof claims === "object" && !Array.isArray(claims) ? (claims as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}
