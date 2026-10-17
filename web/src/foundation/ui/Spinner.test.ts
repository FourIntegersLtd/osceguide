import assert from "node:assert/strict";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

// node:test cannot import JSX, so these read the source, like the other design guards.
const read = (file: string) => readFileSync(new URL(file, import.meta.url), "utf8");

test("spinner is the ClinicalBuddy arrow icon, spinning, with no border ring", () => {
  const src = read("./Spinner.tsx");
  assert.match(src, /HiOutlineArrowPath/);
  assert.match(src, /\banimate-spin\b/);
  assert.match(src, /role="status"/);
  assert.match(src, /aria-label=\{label\}/);
  assert.match(src, /aria-hidden/);
  assert.doesNotMatch(src, /\bborder-/);
});

test("page and shell loading states use the lg spinner in a muted colour", () => {
  const files = [
    "./AsyncBoundary.tsx",
    "../../app/loading.tsx",
    "../routing/Redirecting.tsx",
    "../../app/app/[workspace]/layout.tsx",
    "../../app/app/[workspace]/page.tsx",
    "../../app/app/[workspace]/screen.tsx",
    "../session/guards.tsx",
    "../../surfaces/ShellFallback.tsx",
  ];
  for (const file of files) {
    assert.match(read(file), /<Spinner [^>]*size="lg"[^>]*text-ink-subtle/, file);
  }
});

test("LoadingSpinner no longer exists anywhere in src", () => {
  assert.equal(existsSync(new URL("./LoadingSpinner.tsx", import.meta.url)), false);
  const walk = (dir: string): string[] =>
    readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
      e.isDirectory() ? walk(`${dir}/${e.name}`) : [`${dir}/${e.name}`],
    );
  const root = fileURLToPath(new URL("../..", import.meta.url));
  const hits = walk(root).filter((f) => !f.endsWith("ui/Spinner.test.ts") && /\.(tsx?|mdx?)$/.test(f) && readFileSync(f, "utf8").includes("LoadingSpinner"));
  assert.deepEqual(hits, []);
});
