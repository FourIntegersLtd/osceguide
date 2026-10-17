/**
 * Where an anonymous visitor is sent from a page that requires a session.
 *
 * A first visit has never held a token, so the login page is just a sign-in.
 * `sessionExpired` is only true when a stored token was presented and refused,
 * which is the one case the page should explain.
 */
export function loginHref(pathname: string, sessionExpired: boolean): string {
  const next = encodeURIComponent(pathname || "/");
  if (!sessionExpired) return `/login?next=${next}`;
  return `/login?next=${next}&reason=session_expired`;
}

/** A destination chosen at sign-out (`/login?deleted=1`), and the page it was chosen on. */
export type SignedOut = { to: string; from: string };

/**
 * Where RequireSession sends someone who just signed out, or null for the usual `loginHref`.
 *
 * Only on the page they signed out from: once they move on, a protected page they open (an in-app
 * link, no reload) is a fresh visit and keeps its `next`, not the old sign-out's destination.
 */
export function signedOutDestination(signedOut: SignedOut | null, pathname: string): string | null {
  return signedOut && signedOut.from === pathname ? signedOut.to : null;
}
