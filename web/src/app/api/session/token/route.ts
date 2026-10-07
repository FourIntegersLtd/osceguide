import { NextResponse, type NextRequest } from "next/server";

import { platformApiUrl } from "@/foundation/platform-client/client";
import { refreshTokenPair, type RefreshedPair } from "@/foundation/platform-client/refreshTokenPair";
import {
  REFRESH_MARGIN_MS,
  clearSessionCookies,
  readSessionCookies,
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
 */

export const dynamic = "force-dynamic";

function noSession(): NextResponse {
  return NextResponse.json({ access_token: null }, { status: 200 });
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  const { accessToken, refreshToken, expiresAt } = readSessionCookies(request);

  if (accessToken && expiresAt && Date.now() < expiresAt - REFRESH_MARGIN_MS) {
    return NextResponse.json({ access_token: accessToken, expires_at: expiresAt });
  }
  if (!refreshToken) return noSession();

  let pair: RefreshedPair | null;
  try {
    pair = await refreshTokenPair(platformApiUrl(), refreshToken);
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
    // A refused refresh means the chain is spent or revoked. Dropping it sends
    // the next call back through sign-in rather than retrying a token that
    // will never work again.
    return clearSessionCookies(noSession());
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
