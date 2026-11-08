import { createHash } from "node:crypto";

import { NextResponse, type NextRequest } from "next/server";

import { platformApiUrl } from "@/foundation/platform-client/client";
import { refreshTokenPair, type RefreshedPair } from "@/foundation/platform-client/refreshTokenPair";
import {
  REFRESH_MARGIN_MS,
  clearSessionCookies,
  readSessionCookies,
  readTokenClaims,
  writeSessionCookies,
} from "@/foundation/platform-client/sessionCookies";

/**
 * The current access token, refreshed here if it is due.
 *
 * Answering from the stored access token whenever it is still good is what
 * keeps the refresh token from being spent on every reload and every new tab.
 * Refresh tokens are single-use with reuse detection, so two spends of the
 * same token read as theft and revoke the whole chain — the bug that used to
 * sign people out on reload. The browser serialises its tabs with a Web Lock
 * before calling here; by the time the second tab arrives the cookie already
 * holds the new token and no second refresh happens.
 *
 * `POST` rather than `GET` so nothing caches it and no cross-site navigation
 * can reach it — `SameSite=Lax` sends the cookie on a top-level GET but never
 * on a cross-site POST.
 *
 * A refused refresh does not clear the cookies straight away. The browser may
 * have stored a newer pair while the refresh was in flight (a sign-in or a
 * password change in another tab: `POST /api/session` does not take the tab
 * lock), and clearing would sign that out. The answer names the refused token
 * by fingerprint instead; the client asks again with it, and only if the
 * cookie *then* still holds that token are the cookies cleared.
 */

export const dynamic = "force-dynamic";

function noSession(): NextResponse {
  return NextResponse.json({ access_token: null }, { status: 200 });
}

/** Names a refresh token without handing it to script. */
function fingerprint(refreshToken: string): string {
  return createHash("sha256").update(refreshToken).digest("hex").slice(0, 32);
}

/** The fingerprint a client sends back after a refused refresh, if any. */
async function refusedEarlier(request: NextRequest): Promise<string | null> {
  try {
    const body = (await request.json()) as { refused?: unknown };
    return typeof body.refused === "string" ? body.refused : null;
  } catch {
    return null;
  }
}

/**
 * The workspace the expired access token was in, read without verifying it: it is only a request
 * to platform-api, which keeps it if the person still holds that membership. `undefined` when the
 * token is missing or unreadable, which gives the default workspace.
 */
function lastWorkspace(accessToken: string | undefined): string | null | undefined {
  const active = readTokenClaims(accessToken)?.active_org;
  if (active === null) return null;
  return typeof active === "string" ? active : undefined;
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  const { accessToken, refreshToken, expiresAt } = readSessionCookies(request);
  const refused = await refusedEarlier(request);

  // The second ask after a refusal: the cookie still holds the refused token,
  // so nothing newer arrived meanwhile and the chain really is gone.
  if (refused && refreshToken && fingerprint(refreshToken) === refused) {
    return clearSessionCookies(noSession());
  }

  if (accessToken && expiresAt && Date.now() < expiresAt - REFRESH_MARGIN_MS) {
    return NextResponse.json({ access_token: accessToken, expires_at: expiresAt });
  }
  if (!refreshToken) return noSession();

  let pair: RefreshedPair | null;
  try {
    pair = await refreshTokenPair(platformApiUrl(), refreshToken, lastWorkspace(accessToken));
  } catch {
    // platform-api unreachable. The chain is probably fine, so the cookies
    // stay and the caller can try again rather than being signed out by a
    // blip. An expired access token means the caller gets nothing for now.
    return NextResponse.json(
      { code: "transport_error", message: "Could not reach the server" },
      { status: 503 },
    );
  }

  if (!pair) {
    // A refused refresh means the chain is spent or revoked. On a first ask
    // the client checks back (see above) before anything is cleared; on the
    // check-back the token was read in this very request, so it goes.
    if (refused) return clearSessionCookies(noSession());
    return NextResponse.json({ access_token: null, refused: fingerprint(refreshToken) });
  }

  const next = {
    accessToken: pair.access_token,
    refreshToken: pair.refresh_token,
    expiresAt: Date.now() + pair.expires_in * 1000,
  };
  return writeSessionCookies(
    NextResponse.json({ access_token: next.accessToken, expires_at: next.expiresAt }),
    next,
  );
}
