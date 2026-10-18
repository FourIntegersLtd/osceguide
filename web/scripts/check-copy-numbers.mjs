// Is a number shown in UI copy typed once, or retyped wherever it is shown?
//
// "At least 12 characters", "30 days", "10 minutes" are server rules and product timings. Typed
// into JSX text and strings they drift from the rule (the form once said 8 while the server wanted
// 12). A numeric literal followed by characters / minutes / hours / days / stations in a .tsx file
// must therefore be one of:
//   - absent: the number comes from a constant or from the API's PlanRead. Constants live in
//     foundation/config/copyNumbers.ts when several features show them, in the owning capability's
//     limits.ts (peer-practice, media) when one does, or beside the rule (session/temporaryPassword.ts); or
//   - in ALLOWED, with the reason the number belongs to that one sentence and no rule.
//
// Constant files are .ts, so they are never scanned. Comment lines are skipped. Allow-list keys are
// "path: matched text"; the list only shrinks.
//
// Usage: node scripts/check-copy-numbers.mjs

import { allowList, COPY_NUMBER, finish, read, rel, sourceFiles } from "./lib-src.mjs";

const ALLOWED = allowList(
  {
    "src/capabilities/account/Achievements.tsx: 3 days": "a streak badge's own threshold, one sentence, no server rule",
    "src/domains/marketing/CascLandingPage.tsx: 7 min": "CASC exam format figure on its own landing page",
    "src/domains/marketing/CascLandingPage.tsx: 4 min": "CASC exam format figure on its own landing page",
    "src/domains/marketing/CascLandingPage.tsx: 16 stations": "CASC exam format figure on its own landing page",
    "src/domains/marketing/PlabLandingPage.tsx: 2 stations": "matched from '100+ PLAB 2 stations': the exam's name, not a count",
    "src/domains/marketing/PlabLandingPage.tsx: 2 station": "matched from 'PLAB 2 station': the exam's name, not a count",
    "src/domains/marketing/institutions/components/InstitutionsHeroCircuitShowcase.tsx: 6 stations": "illustrative circuit in a hero mock-up",
    "src/domains/train/mocks/MockSessions.tsx: 12 minutes": "TODO: station length belongs to the exam config / PlanRead, not copy",
    "src/foundation/ui/ProgressBar.tsx: 3 stations": "TODO: example session size; also disagrees with the 12 minutes above (3 x 12 is not 45)",
    "src/foundation/ui/ProgressBar.tsx: 45 minutes": "TODO: see 3 stations",
  },
  10,
);

const offenders = [];
for (const file of sourceFiles().filter((f) => f.endsWith(".tsx"))) {
  read(file).split("\n").forEach((line, i) => {
    if (/^\s*(\/\/|\/?\*)/.test(line)) return;
    for (const m of line.replace(/\s\/\/\s.*$/, "").matchAll(COPY_NUMBER)) {
      if (!ALLOWED.has(`${rel(file)}: ${m[0]}`)) offenders.push(`${rel(file)}:${i + 1}  "${m[0]}"`);
    }
  });
}

finish("check-copy-numbers", offenders, ALLOWED);
