import assert from "node:assert/strict";
import test from "node:test";
import {
  allowList,
  apiConsts,
  COPY_NUMBER,
  expand,
  normPath,
  pathHelpers,
  pathMatches,
  sharedPathHelpers,
  permissionGates,
  rel,
  sourceFiles,
  templatePath,
} from "./lib-src.mjs";

test("allowList counts, remembers use, and reports unused entries", () => {
  const list = allowList({ a: "x", b: "y" }, 2);
  assert.equal(list.size, 2);
  assert.equal(list.has("a"), true);
  assert.equal(list.has("zzz"), false);
  assert.deepEqual(list.stale(), ["b"]);
});

test("normPath turns parameters into {} and drops the query", () => {
  assert.equal(normPath("/api/v1/orgs/{org_slug}/sso?x=1"), "/api/v1/orgs/{}/sso");
  assert.equal(normPath("/a/${id}/b"), "/a/{}/b");
});

test("templatePath resolves constants, drops glued queries, tails run-time prefixes", () => {
  assert.deepEqual(templatePath("${P}/orgs/${slug}", { P: "/api/v1/platform" }), { full: true, path: "/api/v1/platform/orgs/{}" });
  assert.deepEqual(templatePath("/api/v1/me/sittings${orgQuery(x)}"), { full: true, path: "/api/v1/me/sittings" });
  assert.deepEqual(templatePath("${scope.base}/exams/${pathId(e)}"), { full: false, path: "/exams/{}" });
  assert.equal(templatePath("hello"), null);
});

test("sourceFiles lists source but not tests or declaration files", () => {
  const files = sourceFiles().map(rel);
  assert.ok(files.includes("src/foundation/platform-client/client.ts"));
  assert.ok(!files.some((f) => /\.test\.tsx?$/.test(f) || f.endsWith(".d.ts")));
});

test("COPY_NUMBER finds a number beside a unit word and ignores class names", () => {
  const hits = (text) => [...text.matchAll(COPY_NUMBER)].map((m) => m[0]);
  assert.deepEqual(hits("within 30 days, or 7 to 10 min, at least 12 characters"), ["30 days", "7 to 10 min", "12 characters"]);
  assert.deepEqual(hits('className="h-7 min-w-7" {n} days v1.2 days'), []);
});

test("permissionGates counts a positive check on a permission that grants the rung", () => {
  assert.equal(permissionGates('if (can(session, "manage_team")) save();').has("org_admin"), true);
  assert.equal(permissionGates("return isPlatformAdmin(session) && <Button />;").has("platform_admin"), true);
});

test("permissionGates ignores a negated check and a permission that does not grant the rung", () => {
  assert.equal(permissionGates('if (!can(session, "manage_team")) return null;').has("org_admin"), false);
  assert.equal(permissionGates("if (!isPlatformAdmin(session)) return;").has("platform_admin"), false);
  assert.equal(permissionGates('can(session, "read_org") && save()').has("org_admin"), false);
  assert.equal(permissionGates('can(session, "run_circuits") && save()').has("org_admin"), false);
  assert.equal(permissionGates('can(session, "export_results") && save()').has("platform_admin"), false);
});

test("apiConsts reads a file's /api/v1 path constants", () => {
  assert.deepEqual(apiConsts('const BASE = "/api/v1/me";\nconst X = "other";'), { BASE: "/api/v1/me" });
});

test("expand spells out a file's own and an aliased path builder", () => {
  const source = "const org = (slug: string) => `/api/v1/orgs/${slug}`;\nexport const orgPath = org;";
  const helpers = pathHelpers(source);
  assert.equal(expand("${orgPath(slug)}/members", helpers), "/api/v1/orgs/${slug}/members");
  assert.equal(expand("${other(slug)}/members", helpers), "${other(slug)}/members");
});

test("sharedPathHelpers drops a builder two files define differently", () => {
  const a = "const org = (s) => `/api/v1/orgs/${s}`;\nconst me = () => `/api/v1/me`;";
  const b = "const org = (s) => `/api/v1/platform/organizations/${s}`;\nconst me = () => `/api/v1/me`;";
  assert.deepEqual(sharedPathHelpers([a, b]), { me: "/api/v1/me" });
});

test("pathMatches lets a run-time segment stand for any one segment", () => {
  assert.equal(pathMatches("/api/v1/orgs/{}/{}/bulk/revoke", "/api/v1/orgs/{}/trainees/bulk/revoke"), true);
  assert.equal(pathMatches("/api/v1/orgs/{}/trainees", "/api/v1/orgs/{}/trainees/bulk"), false);
  assert.equal(pathMatches("/trainees/bulk", "/api/v1/orgs/{}/trainees/bulk", false), true);
  assert.equal(pathMatches("/members/bulk", "/api/v1/orgs/{}/trainees/bulk", false), false);
});
