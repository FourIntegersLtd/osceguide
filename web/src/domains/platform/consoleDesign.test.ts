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
  { pattern: /<Card\b/, use: "B2CPanelCard or Panel" },
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

// Queue and list screens on the quiet kit (B2CHero, B2CGroupedSection, QuietCard)
// may not slide back to the console kit's Panel, rows, tiles or page header.
const quietKitScreens = [
  "domains/platform/Users.tsx",
  "domains/platform/users/UserGroup.tsx",
  "domains/platform/ReferralPayouts.tsx",
  "capabilities/staff-moderation/ModerationHome.tsx",
  "domains/platform/StationFlags.tsx",
  "domains/platform/MessagesInbox.tsx",
  "domains/platform/Announcements.tsx",
];

const consoleKitNames = [
  "Panel",
  "RowList",
  "Row",
  "RowLink",
  "StatTile",
  "StatGrid",
  "FoldSection",
  "PlatformPageHeader",
];

function importedNames(source: string): string[] {
  const names: string[] = [];
  for (const match of source.matchAll(
    /import\s+(?:type\s+)?\{([^}]*)\}\s+from/g,
  )) {
    for (const part of (match[1] ?? "").split(",")) {
      const name = part.trim().split(/\s+as\s+/)[0];
      if (name) names.push(name);
    }
  }
  return names;
}

test("queue screens on the quiet kit do not import the console kit's panels, rows or tiles", () => {
  const violations: string[] = [];
  for (const file of quietKitScreens) {
    const path = join(srcRoot, file);
    for (const name of importedNames(readFileSync(path, "utf8"))) {
      if (consoleKitNames.includes(name))
        violations.push(`${file} imports ${name}`);
    }
  }
  assert.deepEqual(violations, []);
});

test("importedNames sees a console-kit import", () => {
  const names = importedNames(
    'import { Button, Panel as P } from "@/foundation/ui";',
  );
  assert.deepEqual(names, ["Button", "Panel"]);
});
