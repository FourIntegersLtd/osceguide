import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const srcRoot = join(dirname(fileURLToPath(import.meta.url)), "../..");

const consoleRoots = [
  "domains/platform",
  "capabilities/staff-growth",
  "capabilities/staff-media",
  "capabilities/staff-moderation",
  "capabilities/authoring",
  "capabilities/account/settings",
];

// The kit in foundation/ui owns every colour, radius and form control; a screen that
// reaches past it is how the console drifted into three visual languages before.
const banned: { pattern: RegExp; use: string }[] = [
  {
    pattern: /\bb2c-[a-z]/,
    use: "semantic tokens (text-ink, bg-surface, border-border)",
  },
  {
    pattern: /\bosce-ink-/,
    use: "text-ink / text-ink-muted / text-ink-subtle",
  },
  { pattern: /\bborder-border-strong\b/, use: "border-border" },
  {
    pattern: /\brounded-(control|md|lg)\b/,
    use: "rounded-osce-* or a kit component",
  },
  { pattern: /\btext-(xs|sm|base|lg|xl)\b/, use: "the text-osce-* type scale" },
  { pattern: /<Card\b|B2CPanelCard/, use: "Panel" },
  { pattern: /<select\b/, use: "Select" },
  { pattern: /<textarea\b/, use: "Textarea" },
  { pattern: /type="checkbox"/, use: "Checkbox" },
];

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return sourceFiles(path);
    return /\.tsx?$/.test(name) && !name.endsWith(".test.ts") ? [path] : [];
  });
}

test("the staff console, authoring and settings are built only from the foundation kit", () => {
  const violations: string[] = [];
  for (const root of consoleRoots) {
    for (const file of sourceFiles(join(srcRoot, root))) {
      readFileSync(file, "utf8")
        .split("\n")
        .forEach((line, index) => {
          for (const rule of banned) {
            if (rule.pattern.test(line)) {
              violations.push(
                `${relative(srcRoot, file)}:${index + 1} — use ${rule.use}`,
              );
            }
          }
        });
    }
  }
  assert.deepEqual(violations, []);
});
