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
  { pattern: /\bbg-black\b/, use: "a semantic surface token (a video well is bg-ink)" },
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

// The kit files the console is made of are held to the same scan as the screens.
const consoleKitFiles = [
  "foundation/ui/PlatformConsole.tsx",
  "foundation/ui/platformStaffChrome.ts",
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
  const files = [
    ...consoleRoots.flatMap((root) => sourceFiles(join(srcRoot, root))),
    ...consoleKitFiles.map((file) => join(srcRoot, file)),
  ];
  {
    for (const file of files) {
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

// Queue and list screens on the quiet kit (B2CHero, B2CGroupedSection)
// may not slide back to the console kit's Panel or FoldSection.
const quietKitScreens = [
  "domains/platform/Users.tsx",
  "domains/platform/users/UserGroup.tsx",
  "domains/platform/ReferralPayouts.tsx",
  "capabilities/staff-moderation/ModerationHome.tsx",
  "domains/platform/StationFlags.tsx",
  "domains/platform/MessagesInbox.tsx",
  "domains/platform/Announcements.tsx",
];

const consoleKitNames = ["Panel", "FoldSection"];

// A list of records is a b2b Table and key/value rows are B2CGroupedSection rows, as in assess;
// the divided-row kit is retired everywhere in the console. Add a file here only for a real exception.
const rowKitNames = ["Row", "RowList", "RowLink"];
const rowKitAllowed: string[] = [];

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

test("no console screen draws a divided row list", () => {
  const violations: string[] = [];
  for (const root of consoleRoots.slice(0, 4)) {
    for (const file of sourceFiles(join(srcRoot, root))) {
      const name = relative(srcRoot, file);
      if (rowKitAllowed.includes(name)) continue;
      for (const imported of importedNames(readFileSync(file, "utf8"))) {
        if (rowKitNames.includes(imported)) violations.push(`${name} imports ${imported}`);
      }
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

// Every console screen opens with the assess page header (B2CPageHeader), never its own title.
const consoleScreens = [
  "domains/platform/Overview.tsx",
  "domains/platform/Organizations.tsx",
  "domains/platform/OrganizationDetail.tsx",
  "domains/platform/UserDetail.tsx",
  "domains/platform/Users.tsx",
  "domains/platform/BillingQueue.tsx",
  "domains/platform/Ops.tsx",
  "domains/platform/PlatformAudit.tsx",
  "domains/platform/PlatformTeam.tsx",
  "domains/platform/AttemptInspector.tsx",
  "domains/platform/ReferralPayouts.tsx",
  "domains/platform/StationFlags.tsx",
  "domains/platform/MessagesInbox.tsx",
  "domains/platform/Announcements.tsx",
  "capabilities/staff-moderation/ModerationHome.tsx",
  "capabilities/staff-growth/bmj/BmjDashboard.tsx",
  "capabilities/staff-media/MediaDetailScreen.tsx",
  "capabilities/authoring/templates/PlatformTemplateWizardPageLayout.tsx",
  "foundation/ui/PlatformTabbedScreen.tsx",
];

test("every console screen uses B2CPageHeader and none draws its own h1", () => {
  const violations: string[] = [];
  for (const file of consoleScreens) {
    const source = readFileSync(join(srcRoot, file), "utf8");
    if (!source.includes("<B2CPageHeader")) violations.push(`${file} has no B2CPageHeader`);
    if (/<h1\b/.test(source)) violations.push(`${file} draws its own <h1>`);
  }
  assert.deepEqual(violations, []);
});
