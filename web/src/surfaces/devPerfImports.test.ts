import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const surfacesRoot = dirname(fileURLToPath(import.meta.url));

/**
 * The workspace shell must not static-import `screens.ts`, which used to pull
 * every arm's screen map (and entire domain trees) into the layout chunk.
 */
test("SurfaceShell does not import screens.ts", () => {
  const source = readFileSync(join(surfacesRoot, "SurfaceShell.tsx"), "utf8");
  assert.equal(
    source.includes('from "@/surfaces/screens"'),
    false,
    "SurfaceShell must use navFooters.ts and lazy help instead of screens.ts",
  );
});

test("workspace layout does not import screens.ts", () => {
  const layoutPath = join(surfacesRoot, "../app/app/[workspace]/layout.tsx");
  const source = readFileSync(layoutPath, "utf8");
  assert.equal(
    source.includes('from "@/surfaces/screens"'),
    false,
    "workspace layout must not static-import the screen registry",
  );
});
