/**
 * GET /version — proof of which build answered this request.
 *
 * Staging and production run the same code at different moments, and a
 * Vercel preview runs whatever commit its branch was at. This is the one
 * question "did the deploy I just pushed actually land here?" needs
 * answered, and it needs no session to ask: `VERCEL_GIT_COMMIT_SHA` is set
 * by Vercel on every build — production, staging, and every preview alike —
 * so this answers with the exact commit the running process was built from.
 *
 * Deliberately outside `PRIVATE_PATH_PREFIXES` (`foundation/routing/
 * pathVisibility.ts`) and outside every `RequireSession`-guarded layout
 * (`app/app/[workspace]/layout.tsx`, `app/staff/layout.tsx`): a health check
 * that itself requires signing in is not a health check.
 *
 * Returns a plain `Response` rather than `NextResponse` — the two behave
 * identically for a route this simple, and this one has no cookies or
 * redirects to build, so there is nothing `NextResponse` adds here.
 */

// Never statically rendered or cached: every deploy must answer with its
// *own* commit, not a build-time snapshot baked in once and served forever.
export const dynamic = "force-dynamic";

export function GET(): Response {
  return Response.json({ commit: process.env.VERCEL_GIT_COMMIT_SHA ?? "" });
}
