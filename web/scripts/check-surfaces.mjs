// Does every place the UI points at resolve to a real page or screen?
//
// A nav item, a capability's path or a surface manifest's screenName that names nothing is a link
// that 404s or a screen the manifest promises and the arm never renders (the Hire "My assessments"
// link that led nowhere). Checked: `href("...")` in each src/surfaces/*/surface.ts against
// src/app, capability `path:` values against src/app, and each manifest's screenNames against the
// arm's screen map (platform: against src/app/staff pages).
//
// Allow-lists only shrink: PAGE_ALLOW carries its own ceiling.
//
// Usage: node scripts/check-surfaces.mjs

import { existsSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { allowList, finish, read, rel, root, sourceFiles } from "./lib-src.mjs";

const PAGE_ALLOW = allowList(
  {
    "/debriefs": "REAL GAP: the Debrief nav item links to /debriefs, which has no index page (only /debriefs/[id])",
  },
  1, // lower only
);

const offenders = [];

const appDir = join(root, "src/app/app/[workspace]");
const staffDir = join(root, "src/app/staff");
function hasPage(dir, path) {
  const walk = (cur, segs) => {
    if (!segs.length) return existsSync(join(cur, "page.tsx"));
    const names = readdirSync(cur, { withFileTypes: true }).filter((d) => d.isDirectory()).map((d) => d.name);
    return names.some((n) => (n === segs[0] || /^\[.+\]$/.test(n)) && walk(join(cur, n), segs.slice(1)));
  };
  return walk(dir, path.split("/").filter(Boolean));
}
const kebab = (s) => s.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
const screenKeys = (file) => {
  const m = read(join(root, file)).match(/export const \w+Screens: ScreenMap = \{([\s\S]*?)\n\};?/);
  return new Set([...(m?.[1] ?? "").matchAll(/^\s+(\w+):/gm)].map((x) => x[1]));
};
// Where each arm's pages live, and whose screen map it renders (hire renders assess's).
const ARMS = {
  train: { dir: appDir, screens: "train" },
  assess: { dir: appDir, screens: "assess" },
  hire: { dir: appDir, screens: "assess" },
  partner: { dir: appDir, screens: "partner" },
  platform: { dir: staffDir, screens: null },
};
for (const [arm, { dir, screens }] of Object.entries(ARMS)) {
  const file = `src/surfaces/${arm}/surface.ts`;
  const s = read(join(root, file));
  for (const m of s.matchAll(/\bhref\("([^"]*)"\)/g)) {
    if (!hasPage(dir, m[1])) offenders.push(`nav href "${m[1]}" has no page  (${file})`);
  }
  let names = [...(s.match(/screenNames:\s*\[([^\]]*)\]/)?.[1] ?? "").matchAll(/"(\w+)"/g)].map((x) => x[1]);
  if (arm === "assess" || arm === "hire") {
    const list = read(join(root, "src/surfaces/assess/surface.ts")).match(/ASSESS_SCREEN_NAMES[^=]*=\s*\[([\s\S]*?)\]/)[1];
    names = [...list.matchAll(/"(\w+)"/g)].map((x) => x[1]);
  }
  if (!screens) {
    for (const n of names) {
      const p = n === "dashboard" ? "" : "/" + kebab(n);
      if (!hasPage(staffDir, p)) offenders.push(`screenName "${n}" has no /staff page  (${file})`);
    }
  } else {
    const keys = screenKeys(`src/surfaces/${screens}/screens.tsx`);
    for (const n of names) if (!keys.has(n)) offenders.push(`screenName "${n}" is not in ${screens}Screens  (${file})`);
  }
}
const capDirs = sourceFiles().filter((f) => /capabilit(y|ies)\.ts$|Capability\.ts$|studyCapabilities\.ts$/.test(f));
for (const f of capDirs) {
  for (const m of read(f).matchAll(/^\s+path: "(\/[^"]*)"/gm)) {
    if (!hasPage(appDir, m[1]) && !hasPage(staffDir, m[1]) && !PAGE_ALLOW.has(m[1])) offenders.push(`capability path "${m[1]}" has no page  (${rel(f)})`);
  }
}

finish("check-surfaces", offenders, PAGE_ALLOW);
