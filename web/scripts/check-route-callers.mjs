// Does every request the web sends have a route, and every route the web should call a caller?
//
// Two drifts this stops, both of which shipped once:
//   1. a screen calls a path the API renamed or never had (a 404 only a user finds);
//   2. the API grows a route nobody calls (the feature exists on one side only);
// (Nav items and surface manifests naming pages that do not exist: check-surfaces.mjs.)
//
// Paths are compared as segments with every parameter ("{id}" or "${expr}") as "{}". A call whose
// prefix is built at run time (`${scope.base}/exams`) is matched by its tail, so it is checked less
// strictly than a literal `/api/v1/...` one. Methods are not compared, and a verb passed to a
// request helper ("extend-clock") counts as a caller of any route ending in it: a loose match,
// so a same-named route can hide an uncalled one.
//
// Allow-lists only shrink: ROUTE_ALLOW carries its own ceiling.
//
// Usage: node scripts/check-route-callers.mjs

import {
  allowList,
  apiConsts,
  expand,
  finish,
  literals,
  normPath,
  pathHelpers,
  pathMatches,
  read,
  rel,
  sharedPathHelpers,
  sourceFiles,
  spec,
  templatePath,
} from "./lib-src.mjs";


// ---- routes the web is not expected to call -------------------------------------------------
const INTERNAL_PREFIXES = {
  "/api/worker/": "LiveKit workers call these with a worker key; no browser does",
  "/api/v1/webhooks/": "Stripe and provider webhooks call these, not the web",
  "/api/v1/internal/": "service-to-service",
};
const INTERNAL_EXACT = {
  "/health": "liveness probe",
  "/api/v1/health": "liveness probe",
};
// Routes that are web-facing but have no caller yet. Each needs a reason; the list only shrinks.
const ROUTE_ALLOW = allowList(
  {
    "/api/v1/billing/webhooks/stripe": "Stripe calls it; the path lacks the /webhooks/ prefix the rule above matches",
    "/api/v1/sso/saml/{}/acs": "the identity provider posts here, not a browser fetch",
    "/api/v1/sso/saml/{}/metadata": "the identity provider reads it by URL",
    "/api/v1/orgs/{}/scim/v2/Groups": "SCIM client (the IdP) only",
    "/api/v1/orgs/{}/scim/v2/Groups/{}": "SCIM client (the IdP) only",
    "/api/v1/orgs/{}/scim/v2/ServiceProviderConfig": "SCIM client (the IdP) only",
    "/api/v1/orgs/{}/scim/v2/Users": "SCIM client (the IdP) only",
    "/api/v1/orgs/{}/scim/v2/Users/{}": "SCIM client (the IdP) only",
    "/api/v1/platform/health": "ops probe",
    "/api/v1/platform/voice/capacity": "ops probe / not surfaced on the Ops screen yet",
    "/api/v1/platform/users": "superseded by /platform/directory; kept for staff scripts",
    "/api/v1/platform/generate/podcast": "driven by staff scripts and the media pipeline, no screen",
    "/api/v1/platform/generate/slide-deck": "driven by staff scripts and the media pipeline, no screen",
    "/api/v1/growth/partners/{}/reconciliation": "the summary already carries reconciliation; no separate screen",
    "/api/v1/growth/partners/{}/revenue": "no caller yet: revenue detail beyond revenue-over-time has no screen",
    "/api/v1/growth/partners/{}/spend": "no caller yet: spend entry has no screen",
    "/api/v1/me/receipts/{}": "no caller yet: single receipt view; the list is shown",
    "/api/v1/orgs/{}/circuits/{}/edit-lock": "EditCircuit reads the lock off the circuit read instead",
    "/api/v1/orgs/{}/invoices": "no caller yet: org invoices screen not built",
    "/api/v1/orgs/{}/invoices/{}": "no caller yet: org invoices screen not built",
    "/api/v1/orgs/{}/invoices/{}/po-number": "no caller yet: org invoices screen not built",
    "/api/v1/platform/invoices/{}": "no caller yet: staff invoices screen not built",
    "/api/v1/platform/organizations/{}/invoices": "no caller yet: staff invoices screen not built",
    "/api/v1/orgs/{}/practice-access": "no caller yet: practice access screen not built",
    "/api/v1/orgs/{}/practice-access/bulk": "no caller yet: practice access screen not built",
    "/api/v1/orgs/{}/trainees/bulk/cohort": "no caller yet: bulk cohort assign has no screen",
    "/api/v1/orgs/{}/station-imports/{}": "import status is polled through the list",
    "/api/v1/platform/station-imports/{}": "import status is polled through the list",
    "/api/v1/orgs/{}/trainees/bulk/resend-invitation": "GAP B-36: no screen; the roster resends one invitation at a time",
    "/api/v1/orgs/{}/trainees/bulk/revoke": "GAP B-36: no screen; the roster revokes one trainee at a time",
    "/api/v1/orgs/{}/practice-access/{}/revoke": "no caller by design (B-10): the web uses the /entitlements routes",
    "/api/v1/me/tutor-memory": "the Memory tab left Settings (owner decision 2026-10); the api keeps the routes and erasure still clears the memory",
    "/api/v1/me/tutor-memory/notes/{}": "the Memory tab left Settings (owner decision 2026-10); the api keeps the routes",
    "/api/v1/platform/generate/summary": "driven by staff scripts and the media pipeline, no screen",
  },
  34, // lower only (33 + the two tutor-memory routes parked when the Memory tab was removed)
);

// ---- collect the paths the source spells ----------------------------------------------------
const words = new Set(); // verbs passed to request helpers
const callers = []; // { file, full: bool, segs }
// A path built by a file's own or an imported builder (`${orgs(slug)}/members`) is spelled out,
// as check-route-gates does, so it is matched in full rather than by its tail.
const sharedHelpers = sharedPathHelpers(sourceFiles().map(read));
for (const f of sourceFiles()) {
  const s = read(f);
  if (!/\/api\/v1|platform(Request|Download|Stream)|collectPages/.test(s)) continue;
  const consts = apiConsts(s);
  const helpers = { ...sharedHelpers, ...pathHelpers(s) };
  for (const { text } of literals(s)) {
    if (/[\s…]/.test(text) && !text.startsWith("${")) continue; // prose, not a path
    const p = templatePath(expand(text, helpers), consts);
    if (p) callers.push({ file: rel(f), ...p });
  }
  // A verb handed to a request helper: post<Circuit>(slug, id, "extend-clock", ...)
  for (const m of s.matchAll(/\b(?:post|put|patch|del|send|act)\w*(?:<[^()]*>)?\([^()]*?"([a-z][a-z-]*)"/g)) words.add(m[1]);
}

const routes = Object.keys(spec().paths).map((p) => ({ raw: p, path: normPath(p) }));
const routePrefixes = new Set();
for (const r of routes) {
  const parts = r.path.split("/").filter(Boolean);
  for (let i = 1; i < parts.length; i++) routePrefixes.add("/" + parts.slice(0, i).join("/"));
}

const offenders = [];

// 1. every spelled path resolves
for (const c of callers) {
  // A full path may also be a prefix, a base the caller extends.
  const ok = [...routes.map((r) => r.path), ...(c.full ? routePrefixes : [])].some((r) => pathMatches(c.path, r, c.full));
  if (!ok) offenders.push(`no openapi route for ${c.path}  (${c.file})`);
}

// 2. every web-facing route has a caller
const called = (r) =>
  // A run-time segment ("{}") only stands for a route parameter here: a path whose verb is chosen
  // at run time calls none of its candidates for certain.
  callers.some((c) => (c.full ? c.path === r.path : r.path.endsWith(c.path))) ||
  words.has(r.path.split("/").pop());
for (const r of routes) {
  if (Object.keys(INTERNAL_PREFIXES).some((p) => r.raw.startsWith(p)) || r.raw in INTERNAL_EXACT) continue;
  if (called(r) || ROUTE_ALLOW.has(r.path)) continue;
  offenders.push(`route with no caller: ${r.raw}`);
}

finish("check-route-callers", offenders, ROUTE_ALLOW);
