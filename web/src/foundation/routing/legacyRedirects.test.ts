import assert from "node:assert/strict";
import { existsSync, readdirSync } from "node:fs";
import path from "node:path";
import { describe, it } from "node:test";
import {
  CONSUMER_REDIRECTS,
  PREFIX_REDIRECTS,
  legacyDestination as destination,
  legacyDestination,
} from "@/foundation/routing/legacyRedirects";

/* ----------------------------------------------------------------------- *
 * The route tree, read off the disk.
 *
 * A redirect table is only correct if what it points at exists, and until now
 * nothing here could tell — the tests restated the table's own strings, so the
 * day `sessions` was renamed to `sittings` the suite stayed green and every
 * bookmarked session URL in the product started answering 404. This walks
 * `src/app` instead, so a rule now fails when its destination is deleted or
 * renamed.
 * --------------------------------------------------------------------- */

/** Every routable path as a pattern, with dynamic segments as `*` and route groups removed. */
function routePatterns(dir: string, prefix: string[]): string[] {
  if (!existsSync(dir)) return [];
  const out: string[] = [];
  // The directory itself may be the page — `src/app/page.tsx` is the root.
  if (existsSync(path.join(dir, "page.tsx"))) out.push(prefix.join("/"));
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    // A route group is not part of the URL; a dynamic segment is a wildcard.
    const segment = entry.name.startsWith("(")
      ? prefix
      : [...prefix, entry.name.startsWith("[") ? "*" : entry.name];
    if (entry.name.startsWith("@") || entry.name.startsWith(".")) continue;
    if (existsSync(path.join(dir, entry.name, "page.tsx"))) out.push(segment.join("/"));
    out.push(...routePatterns(path.join(dir, entry.name, ""), segment));
  }
  return out;
}

const ROUTES = routePatterns(path.join(process.cwd(), "src", "app"), []);

/** Whether some page answers this pathname, ignoring any query. */
function answers(url: string): boolean {
  const pathname = url.split("?")[0] ?? "";
  const parts = pathname.split("/").filter(Boolean);
  if (parts.length === 0) return ROUTES.includes("");
  return ROUTES.some((pattern) => {
    const segs = pattern.split("/").filter(Boolean);
    if (segs.length !== parts.length) return false;
    return segs.every((s, i) => s === "*" || s === parts[i]);
  });
}

/**
 * Legacy URLs that between them cover every rule in `PREFIX_REDIRECTS`, plus
 * the shapes a real bookmark actually takes. Each must land on a route that
 * exists *and* settle — see the one-hop test below.
 */
const LEGACY_SAMPLE: readonly [string, string][] = [
  // Consumer roots.
  ["/dashboard", "/app/me/dashboard"],
  ["/practice", "/app/me/dashboard"],
  ["/library", "/app/me/summary"],
  ["/feedbacks", "/app/me/transcripts"],
  ["/feedbacks/abc", "/app/me/transcripts"],
  ["/welcome", "/app/me/dashboard"],
  ["/access", "/app/me/settings?tab=payments"],
  ["/settings/referrals/user/1", "/app/me/settings?tab=referrals"],
  ["/payments/success", "/billing/complete"],
  ["/payments/cancel", "/pricing"],
  // Consumer sub-trees, including the two that are not set ids.
  ["/mocks/m1/stations/e1", "/app/me/mocks/m1/stations/e1"],
  ["/mocks/m1/complete", "/app/me/mocks/m1/complete"],
  ["/mocks/list", "/app/me/mocks"],
  ["/mocks/customise", "/app/me/mocks"],
  ["/mocks/m1/update", "/app/me/mocks/m1"],
  ["/summary/s1", "/app/me/summary"],
  ["/articles", "/blogs"],
  ["/debriefs/d1", "/app/me/debriefs/d1"],
  ["/transcripts/t1", "/app/me/transcripts/t1"],
  ["/community", "/app/me/discussion"],
  ["/community/question/q1", "/app/me/discussion?question=q1"],
  ["/marketplace", "/app/me/marketplace"],
  ["/peers", "/app/me/marketplace"],
  ["/human-practice", "/app/me/marketplace"],
  ["/human-practice/session/s1", "/app/me/marketplace/session/s1"],
  ["/human-practice/session/s1/feedback", "/app/me/marketplace/session/s1/feedback"],
  ["/partner/p1/reporting", "/app/p1/reporting"],
  ["/features/f1", "/"],
  // Back office.
  ["/admin", "/staff"],
  ["/admin/sca/stations", "/staff"],
  ["/admin/partner-attribution", "/staff/growth"],
  ["/users/1", "/staff/users"],
  ["/comments/1", "/staff/moderation"],
  ["/platform/audit", "/staff/audit"],
  // An institution's examination tree: session → sitting, circuit → console.
  ["/b2b/kings/dashboard", "/app/kings/dashboard"],
  ["/b2b/kings/sessions", "/app/kings/sittings"],
  ["/b2b/kings/sessions/new", "/app/kings/sittings/new"],
  ["/b2b/kings/sessions/s1", "/app/kings/sittings/s1"],
  ["/b2b/kings/sessions/s1/edit", "/app/kings/sittings/s1"],
  ["/b2b/kings/sessions/s1/circuits/new", "/app/kings/sittings/s1/circuits/new"],
  ["/b2b/kings/sessions/s1/circuits/c1", "/app/kings/circuits/c1"],
  ["/b2b/kings/sessions/s1/circuits/c1/run", "/app/kings/circuits/c1"],
  [
    "/b2b/kings/sessions/s1/circuits/c1/run/slots/sl1/feedback",
    "/app/kings/slots/sl1/review",
  ],
  ["/b2b/kings/sessions/s1/candidates/t1", "/app/kings/sittings/s1/results"],
  ["/b2b/kings/results", "/app/kings/sittings"],
  ["/b2b/kings/live", "/app/kings/live"],
  ["/b2b/kings/trainees", "/app/kings/trainees"],
  ["/b2b/kings/team/onboard", "/app/kings/team"],
  ["/b2b/kings/stations", "/app/kings/authoring/stations"],
  ["/b2b/kings/templates", "/app/kings/authoring/station-templates"],
  ["/b2b/kings/templates/new", "/app/kings/authoring/station-templates/new"],
  ["/b2b/kings/stations/feedback-templates/new", "/app/kings/authoring/rubrics"],
  // A rostered trainee, who is inside an organisation the token already names.
  ["/b2b/trainee", "/app/me/trainee"],
  ["/b2b/trainee/practice", "/app/me/trainee/practice"],
  ["/b2b/trainee/sessions", "/app/me/trainee"],
  ["/b2b/trainee/sessions/s1", "/app/me/trainee/sittings/s1"],
  ["/b2b/trainee/sessions/s1/result", "/app/me/trainee/results/s1"],
  // A join link names a slot, so the id survives as a query the screen reads.
  ["/b2b/trainee/join/sl1", "/app/me/trainee?slot=sl1"],
  ["/b2b/trainee/join", "/app/me/trainee"],
  ["/b2b/trainee/circuit-feedback", "/app/me/trainee"],
  ["/b2b/trainee/transcript", "/app/me/transcripts"],
  // The console sign-ins, and the workspace picker.
  ["/b2b", "/login"],
  ["/b2b/login", "/login"],
  ["/b2b/platform/login", "/login"],
  ["/b2b/institution/login", "/login"],
  ["/b2b/partner/login", "/login"],
  ["/b2b/practice/kings/login", "/login"],
  /*
   * The real URL, spelled the way Next serves it: the legacy page lived in an
   * `(auth)` route group, which never appears in an address. A sample spelled
   * "/b2b/(auth)/change-password" tested a URL nobody could type, and the day
   * the rule was written against that spelling the real one started landing
   * on /app/change-password — a workspace that does not exist.
   */
  ["/b2b/change-password", "/change-password"],
  ["/b2b/select-workspace", "/app"],
  ["/b2b/institutions", "/institutions"],
  ["/b2b/platform", "/staff"],
  ["/b2b/platform/organizations", "/staff/organizations"],
  // Partners and practice accounts.
  ["/b2b/partner/bmj", "/app/bmj"],
  ["/b2b/partner/bmj/exams", "/app/bmj/authoring/exams"],
  ["/b2b/partner/bmj/users/editors", "/app/bmj/team"],
  ["/b2b/practice/kings/history", "/app/kings/mocks"],
  ["/b2b/practice/kings/exams", "/app/kings/mocks"],
  ["/b2b/practice/kings/mocks/s1/stations/e1", "/app/kings/mocks/s1/stations/e1"],
  // platform-web's own first cut, and the arm prefixes it tried.
  ["/assess/kings/sittings", "/app/kings/sittings"],
  ["/assess/trainee", "/app/me/trainee"],
  ["/hire/acme/sittings", "/app/acme/sittings"],
  ["/app/kings/access", "/app/kings/settings?tab=payments"],
];

describe("legacy redirects", () => {
  it("moves the old consumer root paths under the personal workspace", () => {
    assert.equal(destination("/dashboard"), "/app/me/dashboard");
    assert.equal(destination("/mocks"), "/app/me/mocks");
    assert.equal(destination("/library"), "/app/me/summary");
    assert.equal(destination("/slides"), "/app/me/slides");
    assert.equal(destination("/summary"), "/app/me/summary");
  });

  it("leaves the public blogs pages alone and sends the old articles list to them", () => {
    assert.equal(destination("/blogs"), null);
    assert.equal(destination("/blogs/a-day-in-sca"), null);
    assert.equal(destination("/articles"), "/blogs");
  });

  it("keeps both spellings of the dashboard alive", () => {
    // The first cut of platform-web called it "practice"; the old client
    // called it "dashboard". Neither should 404.
    assert.equal(destination("/practice"), "/app/me/dashboard");
    assert.equal(destination("/dashboard"), "/app/me/dashboard");
  });

  it("renames the words the route tree changed underneath", () => {
    // These four are why this file is a test and not a comment: each one used
    // to copy the old path into a new URL that had no page behind it.
    assert.equal(destination("/b2b/kings/sessions"), "/app/kings/sittings");
    assert.equal(
      destination("/b2b/kings/sessions/s1/circuits/c1/run/slots/sl1/feedback"),
      "/app/kings/slots/sl1/review",
    );
    assert.equal(destination("/b2b/kings/templates/new"), "/app/kings/authoring/station-templates/new");
    assert.equal(destination("/feedbacks"), "/app/me/transcripts");
  });

  it("sends every sample destination to a route that exists", () => {
    // The property the table was actually missing. `answers()` reads the disk,
    // so this fails when a page is renamed and nobody thinks of the redirects.
    assert.ok(ROUTES.length > 40, "the route walk found almost nothing — check APP_ROOT");
    for (const [from, to] of LEGACY_SAMPLE) {
      assert.equal(destination(from), to, `${from} should land on ${to}`);
      assert.ok(answers(to), `${from} → ${to}, and nothing serves ${to}`);
    }
  });

  it("answers a destination for every row in the exact table", () => {
    for (const { from, to } of CONSUMER_REDIRECTS) {
      assert.ok(answers(to), `${from} → ${to}, and nothing serves ${to}`);
    }
  });

  it("reads the staff console before it reads an organisation", () => {
    // `/b2b/platform` must never be understood as an org called "platform".
    assert.equal(destination("/b2b/platform"), "/staff");
    assert.equal(destination("/b2b/platform/organizations"), "/staff/organizations");
    assert.equal(destination("/platform/users"), "/staff/users");
  });

  it("drops the arm prefix from every old workspace URL", () => {
    assert.equal(destination("/b2b/kings/dashboard"), "/app/kings/dashboard");
    assert.equal(destination("/b2b/partner/bmj/exams"), "/app/bmj/authoring/exams");
    assert.equal(destination("/b2b/practice/kings/history"), "/app/kings/mocks");
    assert.equal(destination("/b2b/practice/kings/exams"), "/app/kings/mocks");
    assert.equal(destination("/b2b/practice/kings"), "/app/kings/dashboard");
    assert.equal(destination("/assess/kings/sittings"), "/app/kings/sittings");
    assert.equal(destination("/hire/acme/sittings"), "/app/acme/sittings");
  });

  it("leaves a current address alone", () => {
    assert.equal(destination("/app/me/dashboard"), null);
    assert.equal(destination("/login"), null);
    assert.equal(destination("/"), null);
    assert.equal(destination("/exams/sca"), null);
  });

  it("never answers with the path it was given", () => {
    // A row that maps a path to itself would loop the browser forever. This is
    // the property that makes the table safe to extend without reading it all.
    const samples = [
      ...CONSUMER_REDIRECTS.map((r) => r.from),
      ...LEGACY_SAMPLE.map(([from]) => from),
      "/b2b/kings/sessions",
      "/b2b/platform/audit",
      "/assess/kings",
      "/hire/acme",
      "/platform",
      "/app/me/dashboard",
      "/app/kings/sessions",
      "/staff/users",
      "/",
    ];
    for (const path of samples) {
      const to = legacyDestination(path);
      assert.notEqual(to, path, `${path} redirects to itself`);
    }
  });

  it("sends an old Access bookmark to the Settings tab that replaced it", () => {
    /*
     * Both spellings: the retiring client's root-level `/access`, and the one
     * platform-web itself served for a few weeks before billing moved back
     * under Settings. The second was found by opening it in a browser, where
     * it 404ed — the exact table only covered the first.
     */
    assert.equal(destination("/access"), "/app/me/settings?tab=payments");
    assert.equal(destination("/app/me/access"), "/app/me/settings?tab=payments");
    assert.equal(destination("/app/kings/access"), "/app/kings/settings?tab=payments");
  });

  it("settles after one hop", () => {
    // Following a redirect must never produce another one, or the browser
    // gives up with ERR_TOO_MANY_REDIRECTS and the page is simply gone.
    for (const { from } of CONSUMER_REDIRECTS) {
      const once = legacyDestination(from);
      assert.ok(once, `${from} should redirect`);
      assert.equal(legacyDestination(once), null, `${from} → ${once} → redirects again`);
    }
    for (const [from] of LEGACY_SAMPLE) {
      const once = legacyDestination(from);
      assert.ok(once, `${from} should redirect`);
      assert.equal(legacyDestination(once), null, `${from} → ${once} → redirects again`);
    }
  });

  it("has no duplicate rows", () => {
    const froms = CONSUMER_REDIRECTS.map((r) => r.from);
    assert.equal(new Set(froms).size, froms.length);
    const patterns = PREFIX_REDIRECTS.map((r) => r.pattern.source);
    assert.equal(new Set(patterns).size, patterns.length);
  });
});
