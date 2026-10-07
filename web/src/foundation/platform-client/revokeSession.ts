import { refreshTokenPair } from "@/foundation/platform-client/refreshTokenPair";
import { REFRESH_MARGIN_MS, type TokenPair } from "@/foundation/platform-client/sessionCookies";

/**
 * End the stored session at platform-api, for the sign-out route.
 *
 * `/auth/logout` is an authenticated route: it needs the bearer to know whose
 * chain the refresh token names. Posting the refresh token alone answered 401
 * and revoked nothing, so a signed-out cookie jar left a working thirty-day
 * token behind (A-1). The access token is often stale by the time somebody
 * signs out, so a stale one, or one the API refuses, is renewed first with the
 * refresh token and the logout is sent with the new pair; that rotation keeps
 * the same chain, and the logout then revokes the whole chain.
 *
 * `refused` means the chain could not be renewed: it is already spent or
 * revoked, which the caller logs rather than treating as success.
 */
export type RevokeOutcome = "revoked" | "refused" | "unreachable";

export async function revokeSession(
  apiUrl: string,
  stored: Partial<TokenPair>,
  now: number = Date.now(),
): Promise<RevokeOutcome> {
  const { refreshToken } = stored;
  if (!refreshToken) return "revoked";
  const fresh =
    stored.accessToken && stored.expiresAt && now < stored.expiresAt - REFRESH_MARGIN_MS
      ? stored.accessToken
      : null;

  try {
    if (fresh) {
      const first = await postLogout(apiUrl, fresh, refreshToken);
      if (first.ok) return "revoked";
      if (first.status !== 401) return "refused";
    }
    const pair = await refreshTokenPair(apiUrl, refreshToken);
    if (!pair) return "refused";
    const second = await postLogout(apiUrl, pair.access_token, pair.refresh_token);
    return second.ok ? "revoked" : "refused";
  } catch {
    return "unreachable";
  }
}

function postLogout(apiUrl: string, accessToken: string, refreshToken: string): Promise<Response> {
  return fetch(`${apiUrl}/api/v1/auth/logout`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}
