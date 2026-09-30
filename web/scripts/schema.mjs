// Print a named schema (or list names matching a term) from the generated types.
// Usage: node scripts/schema.mjs MediaItemRead | node scripts/schema.mjs --find media
import { readFileSync } from "node:fs";
const src = readFileSync("src/foundation/platform-client/schema.d.ts", "utf8");
const [flag, term] = process.argv.slice(2);
if (flag === "--find") {
  const names = [...src.matchAll(/^        ([A-Za-z0-9_]+): \{/gm)].map((m) => m[1]);
  console.log(names.filter((n) => n.toLowerCase().includes((term ?? "").toLowerCase())).join("\n"));
  process.exit(0);
}
const start = src.indexOf(`        ${flag}: {`);
if (start < 0) { console.error(`not found: ${flag}`); process.exit(1); }
let depth = 0, i = src.indexOf("{", start);
for (let j = i; j < src.length; j++) {
  if (src[j] === "{") depth++;
  else if (src[j] === "}") { depth--; if (depth === 0) { console.log(src.slice(start, j + 1)); break; } }
}
