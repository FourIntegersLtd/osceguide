// Shared by the check-*.mjs scripts and audit-ledger-routes.mjs: the source walk, the OpenAPI
// document, path normalisation, and allow-lists that can only shrink.
import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");

let specCache;
export const spec = () => (specCache ??= JSON.parse(readFileSync(resolve(root, "../api/openapi.json"), "utf8")));

let filesCache;
/** Non-test source files under src/, excluding the generated schema. Cached. */
export function sourceFiles() {
  if (filesCache) return filesCache;
  const out = [];
  const walk = (dir) => {
    for (const name of readdirSync(dir)) {
      const full = join(dir, name);
      if (statSync(full).isDirectory()) walk(full);
      else if (/\.(ts|tsx)$/.test(name) && !/\.test\.tsx?$/.test(name) && !name.endsWith(".d.ts")) out.push(full);
    }
  };
  walk(join(root, "src"));
  return (filesCache = out);
}

export const rel = (f) => relative(root, f);
export const read = (f) => readFileSync(f, "utf8");

/** A path as segments, every parameter ("{id}" or "${expr}") as "{}", query and empty segments dropped. */
export function normPath(p) {
  return (
    "/" +
    p
      .split("?")[0]
      .split("/")
      .filter(Boolean)
      .map((s) => (/[{$]/.test(s) ? "{}" : s))
      .join("/")
  );
}

/**
 * Whether a called path (from `normPath`) can be this route's. A "{}" the caller spells is a
 * run-time value, so it stands for any one segment; `full: false` matches the route's tail.
 */
export function pathMatches(called, route, full = true) {
  const want = called.split("/").filter(Boolean);
  const have = route.split("/").filter(Boolean);
  if (full ? want.length !== have.length : want.length > have.length) return false;
  const tail = have.slice(have.length - want.length);
  return want.every((seg, i) => seg === "{}" || seg === tail[i]);
}

const BALANCED = String.raw`\$\{(?:[^{}]|\{[^}]*\})*\}`;

/**
 * A template literal's text as a path. `full` when it starts `/api/v1` (after substituting a known
 * `${CONST}` prefix); otherwise the part after a run-time `${base}` prefix, which can only be
 * matched by its tail. A `${query}` glued to the last segment is dropped. Null when not a path.
 */
export function templatePath(text, consts = {}) {
  const t = text
    .replace(new RegExp(`^\\$\\{([A-Z_]+)\\}`), (all, name) => consts[name] ?? all)
    .replace(new RegExp(`(?<=[^/])${BALANCED}$`), "");
  if (t.startsWith("/api/v1")) return { full: true, path: normPath(t) };
  if (!t.startsWith("${")) return null;
  const tail = t.replace(new RegExp(`^${BALANCED}`), "");
  return /^\/[a-z]/.test(tail) ? { full: false, path: normPath(tail) } : null;
}

/** Template/string literals, with `${...}` balanced so `${pathId(x)}` does not end the scan early. */
export function literals(src) {
  const out = [];
  for (let i = 0; i < src.length; i++) {
    const q = src[i];
    if (q !== "`" && q !== '"' && q !== "'") continue;
    let j = i + 1;
    let depth = 0;
    for (; j < src.length; j++) {
      const c = src[j];
      if (c === "\\") { j++; continue; }
      if (q === "`" && c === "$" && src[j + 1] === "{") { depth++; j++; continue; }
      if (depth > 0) { if (c === "}") depth--; continue; }
      if (c === q) break;
      if (q !== "`" && c === "\n") break;
    }
    out.push({ text: src.slice(i + 1, j), at: i });
    i = j;
  }
  return out;
}

/**
 * An allow-list with its ceiling beside it. `max` may only be lowered: a list over its ceiling
 * fails, and so does an entry nothing used (delete it, then lower `max`).
 */
/** A file's `const NAME = "/api/v1..."` path constants, for `templatePath`. */
export function apiConsts(source) {
  const consts = {};
  for (const m of source.matchAll(/\bconst ([A-Z_]+) = [`"'](\/api\/v1[^`"']*)[`"']/g)) consts[m[1]] = m[2];
  return consts;
}

/** Where an import specifier in `from` points, without extension: "@/x/y" -> src/x/y. */
export function resolveSpecifier(from, specifier) {
  if (specifier.startsWith("@/")) return join(root, "src", specifier.slice(2));
  if (specifier.startsWith(".")) return resolve(dirname(from), specifier);
  return null;
}
/** A module's file without its extension or a trailing /index, as `resolveSpecifier` names it. */
export const stem = (f) => f.replace(/\.(ts|tsx)$/, "").replace(/\/index$/, "");

/** File-level path builders: `const orgs = (slug) => `${PLATFORM}/organizations/${slug}``. */
export function pathHelpers(source) {
  const out = {};
  for (const m of source.matchAll(/^(?:export\s+)?const (\w+) = \([^)]*\)(?::\s*\w+)?\s*=>\s*\n?\s*(`[^`]*`)/gm))
    out[m[1]] = m[2].slice(1, -1);
  for (const m of source.matchAll(/^(?:export\s+)?function (\w+)\([^)]*\)(?::\s*\w+)?\s*\{\s*return (`[^`]*`);?\s*\}/gm))
    out[m[1]] = m[2].slice(1, -1);
  // An alias of one of them: `export const orgPath = org;`
  for (const m of source.matchAll(/^(?:export\s+)?const (\w+) = (\w+);/gm)) if (m[2] in out) out[m[1]] = out[m[2]];
  return out;
}

/** The builders every source defines alike: a name two files define differently is left out. */
export function sharedPathHelpers(sources) {
  const shared = {};
  const ambiguous = new Set();
  for (const source of sources)
    for (const [name, text] of Object.entries(pathHelpers(source))) {
      if (name in shared && shared[name] !== text) ambiguous.add(name);
      shared[name] = text;
    }
  ambiguous.forEach((name) => delete shared[name]);
  return shared;
}

const BALANCED_CALL = String.raw`(\w+)\((?:[^()]|\([^()]*\))*\)`;
/** Template text with a leading builder call (`${orgs(slug)}/members`) spelled out, up to 3 deep. */
export function expand(text, helpers) {
  for (let n = 0; n < 3; n++) {
    const m = text.match(new RegExp(`^\\$\\{${BALANCED_CALL}\\}`));
    if (!m || !(m[1] in helpers)) break;
    text = helpers[m[1]] + text.slice(m[0].length);
  }
  return text;
}

// What each permission admits, in the API's rungs (`x-capability`). Mirrors the grants in
// api/app/features/tenancy/service_workspace.py (`capabilities_for`, the `can={...}` table): change
// both together. `author_content` is org admin inside an org and platform admin on the staff
// console, so it admits both; nothing else admits a platform admin but `administer_platform`.
const ORG_STAFF = ["org_member", "org_staff"];
const ORG_ADMIN = [...ORG_STAFF, "org_admin"];
export const PERMISSION_ADMITS = {
  read_org: ["org_member"],
  run_circuits: ORG_STAFF,
  manage_team: ORG_ADMIN,
  schedule_sittings: ORG_ADMIN,
  export_results: ORG_ADMIN,
  author_content: [...ORG_ADMIN, "platform_admin"],
  lead_review: [...ORG_STAFF, "lead_reviewer"],
  sign_off_results: [...ORG_ADMIN, "institution_admin"],
  administer_platform: ["platform_admin"],
};

/**
 * The rungs one stretch of source checks for. Only a positive check counts: `!can(...)` and
 * `!isPlatformAdmin(...)` are refusals, not gates. `capabilityAdmits` maps a capability id to
 * what its page gate admits, for `<Capability id="...">`.
 */
export function permissionGates(text, capabilityAdmits = {}) {
  const out = new Set();
  const add = (perm) => (PERMISSION_ADMITS[perm] ?? []).forEach((r) => out.add(r));
  for (const m of text.matchAll(/(?<![!\w.])can\(\s*[\w.?]+\s*,\s*"(\w+)"\s*\)/g)) add(m[1]);
  for (const m of text.matchAll(/\bpermission=\{?\s*"(\w+)"/g)) add(m[1]);
  if (/(?<![!\w.])isPlatformAdmin\(/.test(text)) add("administer_platform");
  for (const m of text.matchAll(/<Capability\s+id="([^"]+)"/g)) (capabilityAdmits[m[1]] ?? []).forEach((r) => out.add(r));
  return out;
}

export function allowList(entries, max) {
  const reasons = new Map(Object.entries(entries));
  const used = new Set();
  return {
    max,
    get size() {
      return reasons.size;
    },
    has(key) {
      if (!reasons.has(key)) return false;
      used.add(key);
      return true;
    },
    stale: () => [...reasons.keys()].filter((k) => !used.has(k)),
  };
}

/** Print the offenders and the allow-list problems and exit 1, or print ok. */
export function finish(name, offenders, ...lists) {
  const problems = [];
  if (offenders.length) problems.push(`${offenders.length} offender(s):\n  ${offenders.join("\n  ")}`);
  for (const list of lists) {
    if (list.size > list.max) problems.push(`allow-list has ${list.size} entries, ceiling is ${list.max}; allow-lists only shrink.`);
    const stale = list.stale();
    if (stale.length) problems.push(`unused allow-list entries (delete them, then lower the ceiling):\n  ${stale.join("\n  ")}`);
  }
  if (problems.length) {
    console.error(`${name} FAILED\n${problems.join("\n")}`);
    process.exit(1);
  }
  console.log(`${name} ok (${lists.map((l) => `${l.size}/${l.max}`).join(", ")} allow-listed)`);
}

/** A number glued to a unit word in copy: "30 days", "7 to 10 min", "12 characters". Global: use matchAll. */
export const COPY_NUMBER = /(?<![\w.$-])(\d[\d,]*(?:\s?(?:-|–|to)\s?\d+)?\+?)\s(characters|minutes?|mins?|hours?|days?|stations?)(?![-\w])/g;
