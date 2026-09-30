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
