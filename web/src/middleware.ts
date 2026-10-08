import { NextResponse, type NextFetchEvent, type NextRequest } from "next/server";
import { legacyDestination } from "@/foundation/routing/legacyRedirects";
import { signInRedirect } from "@/foundation/routing/sessionGate";
import { SESSION_COOKIES } from "@/foundation/platform-client/sessionCookies";
import { examLandingRewritePath } from "@/foundation/routing/examSubdomainLanding";
import { parseReferralParams } from "@/foundation/attribution/parseReferralParams";
import {
  applyVisitorKeyCookie,
  recordArrival,
  resolveVisitorKey,
} from "@/foundation/attribution/arrivalCapture";
import { buildCspHeader, cspEnforceFromEnv } from "@/foundation/security/contentSecurityPolicy";

/**
 * Answers for the addresses the retiring client is still serving.
 *
 * `frontend/` put consumer screens at the site root and every other arm behind
 * its own prefix; ADR 0002 moved all of them under `/app/<workspace>`. People
 * have those old URLs bookmarked, in emails and on the marketing site, so each
 * one needs an answer rather than a 404.
 *
 * Session checking deliberately does **not** happen here beyond one case: no
 * session cookie at all sends `/app/*` to sign-in (`sessionGate.ts`). A cookie
 * says only that a token exists, not that it is still good or what the person
 * may see, so a redirect decided on its presence would be guessing; the API
 * stays the authority and `RequireSession` does the rest in the browser,
 * against a token the server has just validated.
 */
export function middleware(request: NextRequest, event: NextFetchEvent) {
  /*
   * SEC-006: mint this request's Content-Security-Policy before routing.
   *
   * The nonce has to be forwarded on the *request* headers, not just set on the
   * response: Next reads it off the request's `Content-Security-Policy` header
   * during render and stamps it onto its own bootstrap scripts, which is what
   * makes `script-src 'nonce-… strict-dynamic'` load the app instead of blocking
   * it. So every response that renders a page (`next` and the exam rewrite) is
   * built with these forwarded headers; a redirect renders nothing and skips it.
   *
   * It ships Report-Only unless `PLATFORM_WEB_CSP_ENFORCE` is set, and stays so until a staging
   * report window has been reviewed and the violations tuned (A-14 decision) — a nonce CSP
   * forces every page into dynamic rendering, so any statically-rendered page
   * would break silently under enforce until a staging browser pass confirms the
   * whole journey. See `foundation/security/contentSecurityPolicy.ts`.
   */
  const csp = buildCspHeader({
    isDev: process.env.NODE_ENV === "development",
    enforce: cspEnforceFromEnv(process.env.PLATFORM_WEB_CSP_ENFORCE),
  });
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", csp.nonce);
  requestHeaders.set("Content-Security-Policy", csp.value);

  /*
   * First-touch partner attribution, before anything else decides the response.
   *
   * The retiring client did this in `proxy.ts` and this port shipped the parser
   * without the caller, so a visitor from a partner link was recorded nowhere.
   * It is the edge's job rather than a landing component's: the key has to exist
   * before the register form is reached, and a referral landing is the one
   * request where the browser may not run any JavaScript at all.
   */
  const { visitorKey, isFirstTouch } = resolveVisitorKey(request);
  const referral = parseReferralParams({
    host: request.headers.get("host"),
    pathname: request.nextUrl.pathname,
    search: request.nextUrl.search,
  });

  const response = route(request, requestHeaders);

  // The response carries the policy the browser enforces (or reports on); the
  // request carries only the nonce Next needs to render. Both hold one string.
  response.headers.set(csp.name, csp.value);

  if (referral) {
    if (isFirstTouch) {
      applyVisitorKeyCookie(response, visitorKey, request.nextUrl.protocol === "https:");
    }
    // The visitor is already being answered; the ledger entry may arrive after.
    event.waitUntil(recordArrival(referral, visitorKey, request.nextUrl.origin));
  }

  return response;
}

/** The answer this URL needs, ignoring attribution: an old address, an exam host, or itself. */
function route(request: NextRequest, requestHeaders: Headers): NextResponse {
  const signIn = signInRedirect(
    request.nextUrl.pathname,
    request.nextUrl.search,
    request.cookies.has(SESSION_COOKIES.refresh),
  );
  if (signIn) {
    return NextResponse.redirect(new URL(signIn, request.nextUrl.origin), 307);
  }

  const destination = legacyDestination(request.nextUrl.pathname);
  if (destination) {
    const url = request.nextUrl.clone();
    /*
     * A destination may carry a query of its own — `/access` now points at the
     * Settings tab that replaced it — and assigning the whole string to
     * `pathname` percent-encodes the `?`, which lands on a 404 with a literal
     * "%3Ftab=payments" in the address bar. Found by following the redirect in a
     * browser.
     *
     * The destination's query wins over the incoming one: it is the half that
     * says which screen, and nothing sends a query to these old addresses.
     */
    const separator = destination.indexOf("?");
    url.pathname = separator === -1 ? destination : destination.slice(0, separator);
    if (separator !== -1) url.search = destination.slice(separator + 1);

    // 307 rather than 308: these are moves we may revise while the two clients
    // run side by side, and a permanent redirect is cached by browsers forever.
    return NextResponse.redirect(url, 307);
  }

  const rewritePath = examLandingRewritePath(
    request.headers.get("host"),
    request.nextUrl.pathname,
  );
  if (rewritePath) {
    const url = request.nextUrl.clone();
    url.pathname = rewritePath;
    return NextResponse.rewrite(url, { request: { headers: requestHeaders } });
  }

  return NextResponse.next({ request: { headers: requestHeaders } });
}

export const config = {
  matcher: [
    /*
     * Everything except Next's own assets and the files in `public/`. A
     * matcher that listed the old paths instead would have to be edited in two
     * places every time the table grows.
     */
    "/((?!_next/static|_next/image|favicon.ico|api/|images|.*\\.(?:png|jpg|jpeg|gif|svg|webp|ico|txt|xml|json)$).*)",
  ],
};
