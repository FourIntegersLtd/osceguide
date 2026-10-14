import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, it } from "node:test";

const ROOT = process.cwd();
// Staff screens (domains/assess, platform) keep mono for ids and emails by design, so only
// the consumer-facing trees are scanned.
const SCANNED = ["src/capabilities", "src/domains/train"];

/**
 * Where mono stays: ids, codes and editors in staff and authoring screens, and
 * secrets a person copies (recovery codes, the DELETE confirmation). Numbers,
 * dates and timers are Open Sauce with `tabular-nums`, never mono.
 */
const MONO_ALLOWED = [
  "src/capabilities/authoring/",
  "src/capabilities/staff-",
  "src/capabilities/account/mfa/",
  "src/capabilities/account/settings/CloseAccount.tsx",
];

function sources(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return sources(path);
    return /\.tsx?$/.test(name) && !name.endsWith(".test.ts") ? [path] : [];
  });
}

describe("one typeface for numbers", () => {
  it("font-mono appears only in the allowlisted staff, authoring and secret-code screens", () => {
    const offenders = SCANNED.flatMap((dir) => sources(join(ROOT, dir)))
      .map((path) => relative(ROOT, path))
      .filter((path) => !MONO_ALLOWED.some((allowed) => path.startsWith(allowed)))
      .filter((path) => /\bfont-mono\b/.test(readFileSync(join(ROOT, path), "utf8")));
    assert.deepEqual(offenders, []);
  });
});
