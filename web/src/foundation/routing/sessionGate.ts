import { loginHref } from "@/foundation/session/loginHref";

/**
 * Where a visit to the signed-in app goes when the browser holds no session
 * cookie at all, or null to let it through.
 *
 * Only absence is decided here: a cookie says a token exists, not that it is
 * still good or what its holder may see, so every other answer stays with the
 * API and `RequireSession`. This is what stops a signed-out visit rendering the
 * app shell and a spinner before the browser finds out it has no session.
 */
export function signInRedirect(pathname: string, search: string, hasSessionCookie: boolean): string | null {
  const inApp = pathname === "/app" || pathname.startsWith("/app/");
  if (!inApp || hasSessionCookie) return null;
  return loginHref(`${pathname}${search}`, false);
}
