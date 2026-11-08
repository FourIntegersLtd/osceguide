import { NextResponse, type NextRequest } from "next/server";

import { reportError } from "@/foundation/observability/reportError";
import { platformApiUrl } from "@/foundation/platform-client/client";
import { revokeSession } from "@/foundation/platform-client/revokeSession";
import {
  clearSessionCookies,
  readSessionCookies,
  readTokenClaims,
  writeAccessCookies,
  writeSessionCookies,
} from "@/foundation/platform-client/sessionCookies";

/**
 * Adopt and forget the platform session.
 *
 * This is the whole of the BFF: the browser hands a freshly minted pair here
 * once, and from then on the refresh token is the server's business. See
 * `sessionCookies.ts` for why.
 */

/** Never prerendered, never cached: every answer depends on a cookie. */
export const dynamic = "force-dynamic";

interface StoreBody {
  access_token?: unknown;
  refresh_token?: unknown;
  expires_in?: unknown;
}

/** Who a token names, or null. */
function tokenSubject(token: string | undefined): string | null {
  const sub = readTokenClaims(token)?.sub;
  return typeof sub === "string" && sub ? sub : null;
}

/**
 * Only this app's own script may store a session. A cross-site form can post
 * text, urlencoded or multipart without a preflight and would log the victim
 * into the attacker's account (login CSRF), so the body must be declared JSON
 * and an Origin, when the browser sends one, must be this host. Callers with
 * no Origin (server-side, test harnesses) are not a browser-CSRF vector.
 */
function isSameOriginJson(request: NextRequest): boolean {
  if (!request.headers.get("content-type")?.toLowerCase().startsWith("application/json")) return false;
  const origin = request.headers.get("origin");
  if (origin === null) return true;
  try {
    return new URL(origin).host === (request.headers.get("host") ?? request.nextUrl.host);
  } catch {
    return false;
  }
}

/**
 * Store what the platform just issued: a full pair (sign-in, refresh chain
 * start) or, from a workspace switch, an access token alone. The switch
 * continues the refresh chain the cookie already holds, so it is refused when
 * there is no such cookie rather than minting a session out of a bare token.
 */
export async function POST(request: NextRequest): Promise<NextResponse> {
  if (!isSameOriginJson(request)) {
    return NextResponse.json({ code: "forbidden", message: "Cross-site session writes are refused" }, { status: 403 });
  }
  let body: StoreBody;
  try {
    body = (await request.json()) as StoreBody;
  } catch {
    return NextResponse.json({ code: "invalid_request", message: "Expected JSON" }, { status: 400 });
  }

  const accessToken = typeof body.access_token === "string" ? body.access_token : null;
  const refreshToken = typeof body.refresh_token === "string" ? body.refresh_token : null;
  const expiresIn = typeof body.expires_in === "number" ? body.expires_in : null;
  if (!accessToken || expiresIn === null) {
    return NextResponse.json(
      { code: "invalid_request", message: "Expected a token pair" },
      { status: 400 },
    );
  }

  const expiresAt = Date.now() + expiresIn * 1000;
  const reply = new NextResponse(null, { status: 204 });
  if (refreshToken) return writeSessionCookies(reply, { accessToken, refreshToken, expiresAt });

  const held = readSessionCookies(request);
  if (!held.refreshToken) {
    return NextResponse.json(
      { code: "invalid_request", message: "No session to continue" },
      { status: 400 },
    );
  }
  // The switch must continue the chain it came from. Another tab may have
  // signed in as somebody else since; storing this token would put one person's
  // access beside another person's refresh chain.
  const subject = tokenSubject(accessToken);
  if (!subject || subject !== tokenSubject(held.accessToken)) {
    return NextResponse.json(
      { code: "session_changed", message: "The signed-in account changed" },
      { status: 409 },
    );
  }
  return writeAccessCookies(reply, { accessToken, expiresAt });
}

/**
 * Sign out.
 *
 * The refresh token is revoked at platform-api before the cookie goes, because
 * dropping the cookie alone leaves a working thirty-day token in whatever
 * logs or proxies have seen it. The browser cannot do this any more — it has
 * never held the refresh token — so the revocation moved here, which is where
 * it belonged anyway.
 *
 * A failed revoke still clears the cookies: the person asked to be signed out.
 * It is reported, never swallowed: a refresh token that outlives sign-out is
 * the bug this route exists to prevent (A-1).
 */
export async function DELETE(request: NextRequest): Promise<NextResponse> {
  const outcome = await revokeSession(platformApiUrl(), readSessionCookies(request));
  if (outcome !== "revoked") {
    reportError(new Error(`Sign-out could not revoke the refresh chain: ${outcome}`), { area: "session" });
  }
  return clearSessionCookies(new NextResponse(null, { status: 204 }));
}
