/**
 * What the identity provider's redirect back to `/auth/sso/callback` carries.
 *
 * Each broker names its credential its own way: Clerk appends
 * `__clerk_session_token`, Entra's authorization-code redirect appends `code`
 * and echoes the signed `state` the sign-in URL carried. The backend refuses
 * an Entra callback without that `state` (SEC-015), and this page used to
 * drop it and look only for a token, so every Entra sign-in failed (A-2).
 */
export type SsoCallback =
  | { ok: true; orgSlug: string; token: string; state: string | null }
  | { ok: false; message: string };

export function readSsoCallback(params: URLSearchParams): SsoCallback {
  // Entra says why it sent somebody back without a code, e.g. they cancelled.
  if (params.get("error")) {
    return {
      ok: false,
      message: "Your organisation's sign-in did not complete. Please try again.",
    };
  }
  const orgSlug = params.get("org_slug");
  const token = params.get("__clerk_session_token") ?? params.get("code") ?? params.get("token");
  if (!orgSlug || !token) {
    return { ok: false, message: "This sign-in link is incomplete. Please try again." };
  }
  return { ok: true, orgSlug, token, state: params.get("state") };
}
