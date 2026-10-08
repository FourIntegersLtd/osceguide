/** The pair `POST /auth/refresh` answers with. */
export interface RefreshedPair {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

/**
 * Spend a refresh token for a new pair, server side.
 *
 * Refresh tokens are single-use with reuse detection, so whoever calls this
 * must store the answer or end the chain with it. `null` means platform-api
 * refused the token (spent or revoked); a throw means it could not be reached,
 * which leaves the chain as it was. A gateway or server failure (5xx, 429) is the second kind:
 * it says nothing about the token, and reading it as a refusal signed people out of a live session
 * during a deploy. Used by the token route and by sign-out.
 */
export async function refreshTokenPair(apiUrl: string, refreshToken: string): Promise<RefreshedPair | null> {
  const response = await fetch(`${apiUrl}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (response.status >= 500 || response.status === 429) {
    throw new Error(`platform-api answered ${response.status}`);
  }
  if (!response.ok) return null;
  return (await response.json()) as RefreshedPair;
}
