import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

// node:test cannot import JSX, so this reads the source, like the other design guards.
const SRC = fileURLToPath(new URL("../..", import.meta.url));

/** Files that may spin something other than a loading indicator, each with the reason. */
const ALLOWED: Record<string, string> = {
  "foundation/ui/Spinner.tsx": "the one spinner",
  "foundation/ui/Spinner.test.ts": "this guard",
  "foundation/pwa/PullToRefresh.tsx": "the pull gesture rotates the refresh glyph with the finger; it only spins while reloading",
};

const walk = (dir: string): string[] =>
  readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory() ? walk(`${dir}/${e.name}`) : [`${dir}/${e.name}`],
  );

test("no second spinner: animate-spin lives only in foundation/ui/Spinner.tsx", () => {
  const hits = walk(SRC)
    .filter((f) => /\.(tsx?|css)$/.test(f))
    .map((f) => f.slice(SRC.length + 1))
    .filter((f) => !(f in ALLOWED) && readFileSync(`${SRC}/${f}`, "utf8").includes("animate-spin"));
  assert.deepEqual(hits, [], "use <Spinner /> from @/foundation/ui instead of animate-spin");
});
