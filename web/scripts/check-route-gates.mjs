// Does every screen that can send a write the API will refuse check the permission first?
//
// The "supervisor sees a button that 403s" family. platform-api publishes each route's minimum
// role as `x-capability` (api/app/core/openapi.py, `minimum_role`). For every mutating call
// (POST/PUT/PATCH/DELETE) the web makes, this finds the route, its rung, and every screen that
// can reach the call, and asks whether each path to it passes a check that only admits that rung:
// `can(session, "<permission>")`, `isPlatformAdmin(...)`, `<RequireCapability permission=...>`,
// `<Capability id=...>` (the capability's declared permission), or a `layout.tsx` above the page.
//
// Granularity is the top-level declaration: a check anywhere in a component counts for all of it,
// and a component is gated when it checks itself or when every component that uses it is gated
// (a local wrapper such as `AdminsOnly` passes its check to the components it wraps). Paths are
// matched as check-route-callers does, a run-time `${base}` prefix by its tail (a file's own path
// builders such as `orgs(slug)` are spelled out first); a call that could reach two routes passes
// only when both are gated. A path or method chosen at run time is reported unresolved.
//
// `signed_in` and `org_member` need no check: every page sits behind RequireSession, and an org
// workspace only resolves for its members. Allow-lists only shrink: GATE_ALLOW carries its ceiling.
//
// Usage: node scripts/check-route-gates.mjs

import { dirname, join } from "node:path";
import {
  allowList,
  apiConsts,
  expand,
  finish,
  literals,
  normPath,
  pathHelpers,
  pathMatches,
  PERMISSION_ADMITS,
  permissionGates,
  read,
  rel,
  resolveSpecifier,
  root,
  sharedPathHelpers,
  sourceFiles,
  spec,
  stem,
  templatePath,
} from "./lib-src.mjs";

const MUTATING = ["POST", "PUT", "PATCH", "DELETE"];
const NEEDS_NO_CHECK = new Set(["public", "worker", "signed_in", "org_member"]);

// ---- calls already known to reach a screen that does not check ----------------------------
// Keyed "METHOD route  (file#function)". Each needs a reason; the list only shrinks.
const GATE_ALLOW = allowList(
  {
    "POST /api/v1/orgs/{org_slug}/station-imports  (src/capabilities/authoring/api/imports.ts#uploadStationImport)":
      "Gated at the control, not the handler: ImportStationDialog mounts only from the import button inside AuthoringSectionLead (author only)",
    "POST /api/v1/orgs/{org_slug}/station-imports/{import_id}/station  (src/capabilities/authoring/api/imports.ts#draftStationFromImport)":
      "Gated at the control, not the handler: ImportStationDialog mounts only from the import button inside AuthoringSectionLead (author only)",
    "POST /api/v1/orgs/{org_slug}/stations/{station_id}/versions/{version}/archive  (src/capabilities/authoring/api/stations.ts#archiveStationVersion)":
      "Gated at the control, not the handler: fired only from the `write` Archive AuthoringIconAction (StationsTable, StationDetail row actions)",
    "POST /api/v1/orgs/{org_slug}/station-templates/{template_id}/copy  (src/capabilities/authoring/api/templates.ts#copyStationTemplate)":
      "Gated at the control, not the handler: fired only from StationTemplatesSection's `write` AuthoringRowActions (or the import dialog, author only)",
    "POST /api/v1/orgs/{org_slug}/station-templates/{template_id}/publish  (src/capabilities/authoring/api/templates.ts#publishStationTemplate)":
      "Gated at the control, not the handler: fired from StationTemplatesSection's `write` AuthoringRowActions, the import dialog (author only), and StationTemplateNewScreen (inside RequireAuthor)",
    "POST /api/v1/orgs/{org_slug}/station-templates/{template_id}/versions  (src/capabilities/authoring/api/templates.ts#addStationTemplateVersion)":
      "Gated at the control, not the handler: fired only from StationTemplatesSection's `write` AuthoringRowActions (or the import dialog, author only)",
    "DELETE /api/v1/orgs/{org_slug}/station-templates/{template_id}/versions/{version}  (src/capabilities/authoring/api/templates.ts#deleteStationTemplateVersion)":
      "Gated at the control, not the handler: fired only from StationTemplatesSection's `write` AuthoringRowActions (or the import dialog, author only)",
    "POST /api/v1/orgs/{org_slug}/station-templates/{template_id}/versions/{version}/archive  (src/capabilities/authoring/api/templates.ts#archiveStationTemplateVersion)":
      "Gated at the control, not the handler: fired only from StationTemplatesSection's `write` AuthoringRowActions (or the import dialog, author only)",
    "PATCH /api/v1/me/station-sets/{set_id}  (src/domains/train/api.ts#updateSet)":
      "Hidden for learners (2026-10-14): the edit screen's only entry points are commented out and its route redirects; the api refuses non-admins",
    "DELETE /api/v1/me/station-sets/{set_id}  (src/domains/train/api.ts#deleteSet)":
      "Hidden for learners (2026-10-14): SessionCardActions is no longer rendered; the api refuses non-admins",
    "src/capabilities/staff-media/api.ts#generateContent":
      "Takes its path as an argument; its one caller, generateBlog, passes /platform/generate/blog, reached from the staff console only",
  },
  11,
);

/** What a check must admit: the rung, or `rung|platform` when a platform admin also passes. */
function need(op) {
  const rung = op["x-capability"] ?? "public";
  return op["x-platform-admin"] ? `${rung}|platform` : rung;
}

/** Whether a set of admitted rungs satisfies a need from `need()`. */
function passes(gates, needed) {
  const [rung, platform] = needed.split("|");
  return (
    gates.has(rung) || (platform !== undefined && gates.has("platform_admin"))
  );
}

// ---- routes ----------------------------------------------------------------------------------
const routes = [];
for (const [path, item] of Object.entries(spec().paths)) {
  for (const [method, op] of Object.entries(item)) {
    if (MUTATING.includes(method.toUpperCase()))
      routes.push({
        method: method.toUpperCase(),
        raw: path,
        path: normPath(path),
        rung: op["x-capability"] ?? "public",
        need: need(op),
      });
  }
}

// ---- capabilities: id -> what their page gate admits -----------------------------------------
const capabilityAdmits = {};
for (const f of sourceFiles().filter((f) => f.endsWith("/capability.ts"))) {
  const s = read(f);
  const id = s.match(/\bid:\s*"([^"]+)"/)?.[1];
  const perm = s.match(/\bpermission:\s*(null|"[^"]+"|\[[^\]]*\])/)?.[1];
  if (!id || !perm || perm === "null") continue;
  const names = [...perm.matchAll(/"(\w+)"/g)].map((m) => m[1]);
  // Any-of: the page opens for the weakest, so it admits only what every one of them admits.
  capabilityAdmits[id] = names
    .map((n) => PERMISSION_ADMITS[n] ?? [])
    .reduce((a, b) => a.filter((r) => b.includes(r)));
}

// ---- declarations ------------------------------------------------------------------------------
const DECL =
  /^(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function\*?\s+(\w+)|const\s+(\w+)|let\s+(\w+)|class\s+(\w+)|function\s*\()/gm;

const files = new Map(); // file -> { header, decls: [{ name, text, gates }] }
for (const f of sourceFiles()) {
  // Re-exports belong to no declaration; left in, they would read as a use of the name.
  const s = read(f).replace(
    /^export\s+(?:type\s+)?(?:\{[^}]*\}|\*)(?:\s+from\s+["'][^"']+["'])?;?$/gm,
    "",
  );
  const starts = [...s.matchAll(DECL)];
  const header = s.slice(0, starts[0]?.index ?? s.length);
  const decls = starts.map((m, i) => {
    const text = s.slice(m.index, starts[i + 1]?.index ?? s.length);
    return {
      name: m[1] ?? m[2] ?? m[3] ?? m[4] ?? "default",
      text,
      gates: permissionGates(text, capabilityAdmits),
    };
  });
  // A local wrapper (`AdminsOnly`) that checks and renders its children passes the check on.
  for (const d of decls) {
    for (const w of decls) {
      if (
        w !== d &&
        w.gates.size &&
        /\bchildren\b/.test(w.text) &&
        new RegExp(`<${w.name}[\\s>]`).test(d.text)
      )
        w.gates.forEach((r) => d.gates.add(r));
    }
  }
  files.set(f, { header, decls, source: s });
}
// A hook or predicate that only wraps a check (`useCanAuthor`, `mayEdit`) is a check where it is called.
const helpers = [...files.values()]
  .flatMap(({ decls }) => decls)
  .filter((d) => d.gates.size && /^(use|can|may|is)[A-Z]/.test(d.name));
for (const { decls } of files.values()) {
  for (const d of decls) {
    for (const h of helpers)
      if (h !== d && new RegExp(`\\b${h.name}\\(`).test(d.text))
        h.gates.forEach((r) => d.gates.add(r));
  }
}
// A guard component anywhere (`RequireAuthor`) that renders its children only when the check
// passes (`check ? children : refusal`) is a check where it is rendered.
const guards = [...files.values()]
  .flatMap(({ decls }) => decls)
  .filter(
    (d) =>
      d.gates.size &&
      /^[A-Z]/.test(d.name) &&
      /\?\s*children\s*:|&&\s*children\b/.test(d.text),
  );
for (const { decls } of files.values()) {
  for (const d of decls) {
    for (const g of guards)
      if (g !== d && new RegExp(`<${g.name}[\\s>]`).test(d.text))
        g.gates.forEach((r) => d.gates.add(r));
  }
}

// ---- who uses a declaration --------------------------------------------------------------------
/** Whether file `g` imports `name` from a module that is, or re-exports from above, file `f`. */
function importsFrom(g, name, f) {
  const target = stem(f);
  for (const m of files
    .get(g)
    .source.matchAll(
      /import\s*(?:type\s+)?([\s\S]*?)\s*from\s*["']([^"']+)["']|import\(\s*["']([^"']+)["']\s*\)/g,
    )) {
    const spec = m[2] ?? m[3];
    if (
      m[1] !== undefined &&
      !new RegExp(`\\b${name}\\b`).test(m[1]) &&
      !/^\w+$/.test(m[1].trim())
    )
      continue;
    const at = resolveSpecifier(g, spec);
    if (at && (target === at || target.startsWith(at + "/"))) return true;
  }
  return false;
}

const usersCache = new Map();
function usersOf(f, decl) {
  const key = `${f}#${decl.name}`;
  if (usersCache.has(key)) return usersCache.get(key);
  const word = new RegExp(`\\b${decl.name}\\b`);
  const out = [];
  for (const [g, { decls }] of files) {
    if (decl.name === "default" && g !== f) continue;
    if (
      g !== f &&
      (!word.test(files.get(g).source) || !importsFrom(g, decl.name, f))
    )
      continue;
    for (const d of decls)
      if (d !== decl && word.test(d.text)) out.push([g, d]);
  }
  usersCache.set(key, out);
  return out;
}

/** The rungs the layouts above an app/ route file admit. */
function layoutGates(f) {
  const out = new Set();
  let dir = dirname(f);
  const app = join(root, "src", "app");
  while (dir.startsWith(app)) {
    const layout = [join(dir, "layout.tsx"), join(dir, "layout.ts")].find((p) =>
      files.has(p),
    );
    if (layout)
      files
        .get(layout)
        .decls.forEach((d) => d.gates.forEach((r) => out.add(r)));
    dir = dirname(dir);
  }
  return out;
}

const memo = new Map();
/** Whether every way a person reaches this declaration passes a check admitting only `rung`. */
function gated(f, decl, rung) {
  const key = `${f}#${decl.name}#${rung}`;
  if (memo.has(key)) return memo.get(key);
  memo.set(key, true); // a cycle neither proves nor disproves a path
  let answer;
  if (passes(decl.gates, rung)) answer = true;
  else {
    const users = usersOf(f, decl);
    answer = users.length
      ? users.every(([g, d]) => gated(g, d, rung))
      : passes(layoutGates(f), rung);
  }
  memo.set(key, answer);
  return answer;
}

/** The first ungated chain from a declaration up to a root, for the report. */
function ungatedRoot(f, decl, rung, seen = new Set()) {
  seen.add(`${f}#${decl.name}`);
  const next = usersOf(f, decl).find(
    ([g, d]) => !seen.has(`${g}#${d.name}`) && !gated(g, d, rung),
  );
  return next
    ? ungatedRoot(next[0], next[1], rung, seen)
    : `${rel(f)}#${decl.name}`;
}

// ---- mutating calls ------------------------------------------------------------------------------
/** The text of a call's arguments, split at top-level commas. `open` is the index of its "(". */
function callArgs(text, open) {
  const args = [];
  let depth = 0;
  let start = open + 1;
  for (let i = open; i < text.length; i++) {
    const c = text[i];
    if (c === "`" || c === '"' || c === "'") {
      const lit = literals(text.slice(i))[0];
      i += lit.text.length + 1;
      continue;
    }
    if ("([{".includes(c)) depth++;
    else if (")]}".includes(c)) {
      depth--;
      if (depth === 0)
        return [...args, text.slice(start, i).trim()].filter(Boolean);
    } else if (c === "," && depth === 1) {
      args.push(text.slice(start, i).trim());
      start = i + 1;
    }
  }
  return args;
}

/** A path argument as template text, a bare expression (`orgs(slug)`) as `${...}`. */
const argText = (arg) =>
  arg.startsWith("`") || arg.startsWith('"') ? arg.slice(1, -1) : "${" + arg + "}";

// An imported builder (`orgPath(slug)` from another api.ts) is spelled out too, when its name
// means one thing everywhere.
const sharedHelpers = sharedPathHelpers([...files.values()].map((f) => f.source));

/** The offence, if any, of one mutating call: `call` is the regex match on `platformRequest(`. */
function checkCall(f, decl, call, helpers, consts) {
  const [pathArg = "", options = ""] = callArgs(decl.text, call.index + call[0].length - 1);
  const method = options.match(/\bmethod:\s*(?:"([A-Z]+)"|(\w+))/);
  if (!method || (method[1] && !MUTATING.includes(method[1]))) return null;
  const where = `${rel(f)}#${decl.name}`;
  const path = method[1] ? templatePath(expand(argText(pathArg), helpers), consts) : null;
  if (!path || /^(\/\{\})+$/.test(path.path))
    return GATE_ALLOW.has(where)
      ? null
      : `unresolved ${method[1] ?? method[2]} call in ${where}: spell the route in the call`;
  // A run-time prefix can reach more than one route (`${scope.base}`): each must be gated.
  const needing = routes.filter(
    (r) =>
      r.method === method[1] &&
      pathMatches(path.path, r.path, path.full) &&
      !NEEDS_NO_CHECK.has(r.rung),
  );
  // No route at all is check-route-callers' report.
  if (!needing.length) return null;
  // An export nothing calls reaches no screen, so no screen can skip its check.
  if (!usersOf(f, decl).length && !rel(f).startsWith("src/app/")) return null;
  checked++;
  const open = needing.find((r) => !gated(f, decl, r.need));
  if (!open) return null;
  const key = `${method[1]} ${open.raw}  (${where})`;
  if (GATE_ALLOW.has(key)) return null;
  return `${key} needs ${open.rung}; reached unchecked from ${ungatedRoot(f, decl, open.need)}`;
}

const offenders = [];
let checked = 0;
for (const [f, { decls, source }] of files) {
  const consts = apiConsts(source);
  const helpers = { ...sharedHelpers, ...pathHelpers(source) };
  for (const decl of decls)
    for (const call of decl.text.matchAll(/\bplatform(?:Request|Download)\s*(?:<(?:[^<>]|<[^<>]*>)*>)?\s*\(/g)) {
      const offence = checkCall(f, decl, call, helpers, consts);
      if (offence) offenders.push(offence);
    }
}

console.log(`check-route-gates: ${checked} writes need a check`);
finish("check-route-gates", offenders, GATE_ALLOW);
