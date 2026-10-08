// Is the ledger's map of the API still the API's map?
//
// `docs/BACKLOG.md` names a lot of routes. When a row says a route is served, or cites one as
// the shape a screen waits for, the reader cannot tell which is which without opening
// openapi.json — and the failure this exists to stop is a ledger that quietly understates (or
// overstates) what the backend already does.
//
// So: every `METHOD /path` in that file must either exist in
// openapi.json or be framed, in its own sentence, as absent/future. A route
// named as bare fact that is not in the document is the contradiction worth
// failing on. Legacy Flask paths (`/api/…`, not `/api/v1`) are exempt — those
// are the retiring client's, quoted as history.
//
// Sentences, not lines: the docs are hard-wrapped, so a route is split across
// newlines ("/platform/users/{id}/stations/⏎{station_id}/reset-attempts") and
// the words that mark a proposal ("There is no …", "… would fix both") are
// routinely on the other side of a line break from the route itself. Matching
// per line produced five false accusations on the first run; the fold-then-
// sentence loop is what makes the check agree with what the prose actually says.
//
// Usage: node scripts/audit-ledger-routes.mjs

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { normPath, root, spec } from "./lib-src.mjs";

const DOCS = ["docs/BACKLOG.md"];

// Markdown code spans are written `GET /path` and often broken across lines, so
// a space OR a newline may sit between the verb and the path.
const ROUTE = /\b(GET|POST|PATCH|PUT|DELETE)[ \t]+(\/[\w{}/.\-]+?)(?=[\s`,.)\]]|$)/g;

// A sentence carrying one of these is the ledger *proposing* or *denying* a
// route, not claiming it exists.
const ABSENT =
  /\b(would|will|need|no|not|none|never|absent|missing|open|future|until then|may call|either|cannot|can't|smallest fix|obvious shape|has no caller|nothing calls|not ported|not served|gone)\b/i;

function loadServed() {
  const set = new Set();
  for (const path of Object.keys(spec().paths)) {
    const n = normPath(path);
    set.add(n);
    // The docs abbreviate by dropping the workspace prefix.
    const tail = n.replace(/^\/api\/v1/, "");
    if (tail) set.add(tail);
  }
  return set;
}

function matches(docPath, served) {
  if (served.has(docPath)) return true;
  for (const real of served) {
    if (real === docPath || real.endsWith(docPath) || real.endsWith(`${docPath}/`)) return true;
  }
  return false;
}

// Join a wrapped paragraph back into one string, then split on sentence ends.
// A line ending in "/" is a path broken mid-route ("/stations/⏎{station_id}")
// and rejoins with no space; ordinary wrapped prose rejoins with one.
function sentences(text) {
  const unbroken = text.replace(/\/\n(?=[\w{])/g, "/");
  const logical = unbroken.replace(/([^\n])\n(?!(?:#|>|\||-|\*|\d+\.|$))/g, "$1 ");
  return logical.split(/(?<=\.)\s+|\n/);
}

const served = loadServed();
let failures = 0;
let checked = 0;

for (const doc of DOCS) {
  const text = readFileSync(resolve(root, doc), "utf8");
  for (const sentence of sentences(text)) {
    for (const [, method, raw] of sentence.matchAll(ROUTE)) {
      checked += 1;
      if (raw.startsWith("/api/") && !raw.startsWith("/api/v1")) continue; // legacy
      const target = normPath(raw);
      if (target === "/api/v1/" || target === "/api/v1/{}" || target === "/api/v1") continue;
      if (matches(target, served)) continue;
      if (ABSENT.test(sentence)) continue;
      console.error(`${doc}: asserts "${method} ${raw}" as fact; not in openapi.json`);
      console.error(`  in: ${sentence.trim().slice(0, 160)}`);
      failures += 1;
    }
  }
}

if (failures) {
  console.error(`\nledger route audit failed (${failures} of ${checked} route mentions).`);
  process.exit(1);
}
console.log(`ledger routes agree with openapi.json (${checked} mentions checked).`);
