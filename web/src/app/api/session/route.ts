import { NextResponse, type NextRequest } from "next/server";

import { platformApiUrl } from "@/foundation/platform-client/client";
import {
  clearSessionCookies,
  readSessionCookies,
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

/** Store a pair the platform just issued. */
export async function POST(request: NextRequest): Promise<NextResponse> {
  let body: StoreBody;
  try {
    body = (await request.json()) as StoreBody;
  } catch {
    return NextResponse.json({ code: "invalid_request", message: "Expected JSON" }, { status: 400 });
  }

  const accessToken = typeof body.access_token === "string" ? body.access_token : null;
  const refreshToken = typeof body.refresh_token === "string" ? body.refresh_token : null;
  const expiresIn = typeof body.expires_in === "number" ? body.expires_in : null;
  if (!accessToken || !refreshToken || expiresIn === null) {
    return NextResponse.json(
      { code: "invalid_request", message: "Expected a token pair" },
      { status: 400 },
    );
  }

  return writeSessionCookies(new NextResponse(null, { status: 204 }), {
    accessToken,
    refreshToken,
    expiresAt: Date.now() + expiresIn * 1000,
  });
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
 */
export async function DELETE(request: NextRequest): Promise<NextResponse> {
  const { refreshToken } = readSessionCookies(request);
  if (refreshToken) {
    try {
      await fetch(`${platformApiUrl()}/api/v1/auth/logout`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    } catch {
      // Best effort. The local session goes regardless.
    }
  }
  return clearSessionCookies(new NextResponse(null, { status: 204 }));
}
