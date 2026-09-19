import { NextResponse, type NextRequest } from "next/server";
import { legacyDestination } from "@/foundation/routing/legacyRedirects";

/**
 * Answers for the addresses the retiring client is still serving.
 *
 * `frontend/` put consumer screens at the site root and every other arm behind
 * its own prefix; ADR 0002 moved all of them under `/app/<workspace>`. People
 * have those old URLs bookmarked, in emails and on the marketing site, so each
 * one needs an answer rather than a 404.
 *
 * Session checking deliberately does **not** happen here. The tokens live in
 * `localStorage`, which middleware cannot read, so a redirect decided here
 * would be guessing. `RequireSession` does it in the browser where the answer
 * is actually known.
 */
export function middleware(request: NextRequest) {
  const destination = legacyDestination(request.nextUrl.pathname);
  if (!destination) return NextResponse.next();

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

export const config = {
  matcher: [
    /*
     * Everything except Next's own assets and the files in `public/`. A
     * matcher that listed the old paths instead would have to be edited in two
     * places every time the table grows.
     */
    "/((?!_next/static|_next/image|favicon.ico|images|.*\\.(?:png|jpg|jpeg|gif|svg|webp|ico|txt|xml|json)$).*)",
  ],
};
