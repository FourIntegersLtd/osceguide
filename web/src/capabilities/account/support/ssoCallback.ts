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
  | { ok: false; message: string; ignored?: true };

/** The SAML assertion consumer's code when the IdP's response failed its checks. */
const SAML_REFUSED = "sso_verification_failed";

/**
 * `signedIn`: this browser already holds a session. The link is ignored, and
 * the person told so, rather than their session being swapped for whoever the
 * token names or the link silently doing nothing.
 */
export function readSsoCallback(params: URLSearchParams, { signedIn = false } = {}): SsoCallback {
  if (signedIn) {
    return {
      ok: false,
      ignored: true,
      message:
        "You're already signed in, so this organisation sign-in link was not used. To sign in as someone else, sign out first.",
    };
  }
  const error = params.get("error");
  if (error === SAML_REFUSED) {
    // The response arrived but its signature, audience or timing failed,
    // which retrying alone rarely fixes; that is the IdP's configuration.
    return {
      ok: false,
      message:
        "Your organisation's sign-in could not be confirmed. Try again, and if it keeps happening, ask your IT team to check the single sign-on set-up.",
    };
  }
  // Entra says why it sent somebody back without a code, e.g. they cancelled.
  if (error) {
    return {
      ok: false,
      message: "Your organisation's sign-in did not complete. Please try again.",
    };
  }
  const orgSlug = params.get("org_slug");
  const token = params.get("__clerk_session_token") ?? params.get("code") ?? params.get("token");
  if (!orgSlug || !token) {
    // Also what a reload sees: the page strips the single-use token from the
    // address bar as soon as it has read it.
    return {
      ok: false,
      message: "This sign-in link has already been used or is incomplete. Start again from the sign-in page.",
    };
  }
  return { ok: true, orgSlug, token, state: params.get("state") };
}
