import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, it } from "node:test";

const PAGES = join(process.cwd(), "src/app/app");

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? files(path) : path.endsWith(".tsx") ? [path] : [];
  });
}

describe("page width", () => {
  it("is set once, by the workspace shell: no page under src/app/app sets its own max-w-*", () => {
    const offenders = files(PAGES).filter((path) => /\bmax-w-/.test(readFileSync(path, "utf8")));
    assert.deepEqual(offenders, []);
  });

  it("the shell owns the one page column", () => {
    const shell = readFileSync(join(process.cwd(), "src/surfaces/WorkspaceShell.tsx"), "utf8");
    assert.match(shell, /b2cPageColumn/);
  });

  it("the page column has no width cap or centring: it fills the gutters at any viewport", () => {
    const tokens = readFileSync(join(process.cwd(), "src/foundation/ui/productTokens.ts"), "utf8");
    const column = /export const b2cPageColumn =\s*"([^"]*)"/.exec(tokens)?.[1] ?? "";
    assert.match(column, /\bw-full\b/);
    assert.doesNotMatch(column, /max-w-|mx-auto/);
  });
});
