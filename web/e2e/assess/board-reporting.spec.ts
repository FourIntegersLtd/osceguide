/**
 * Reporting (docs/institution-overhaul/boards/Reporting.dc.html) against the app.
 * Run: E2E_REUSE_SERVER=1 VERIFY_WEB_URL=http://localhost:3109 npx playwright test e2e/assess/board-reporting.spec.ts
 *
 * Named exceptions: (1) spacing per DESIGN.md "Spacing rhythm and quiet selection" (rows 16px, padded cards 24px);
 * (2) the figures under each exam (candidates, pass rate) are data: the seeded exams have sittings but no
 * candidates, so those lines are hidden on both sides; (3) the board's design notes and build spec are display:none.
 */
import { expect, test, type Browser, type Page } from "@playwright/test";
import { compareRegion, openBoard, serveBoards, type BoardServer } from "../support/board-diff";
import { openPage, signedInAs } from "../support/session";
import { seedPeopleOrg, type PeopleOrg } from "../support/seed-people";
import { seedReportingExams } from "../support/seed-settings";

const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1700 },
  { name: "mobile", width: 760, height: 1700 },
] as const;
const APP_PAGE = `xpath=(//h1/parent::div/parent::div)[last()]`;
const SPACING = `.row{padding-top:16px!important;padding-bottom:16px!important}.card.pad{padding:24px!important;gap:16px!important}label{margin-bottom:8px!important}`;

let boards: BoardServer;
let org: PeopleOrg;

test.beforeAll(async () => {
  test.setTimeout(300_000);
  boards = await serveBoards();
  org = await seedPeopleOrg();
  await seedReportingExams(org);
});
test.afterAll(async () => boards?.close());

async function pages(browser: Browser, viewport: { width: number; height: number }, path: string): Promise<{ board: Page; app: Page }> {
  const boardContext = await browser.newContext({ viewport });
  const appContext = await browser.newContext({ viewport });
  await signedInAs(appContext, org.account);
  const board = await boardContext.newPage();
  const app = await appContext.newPage();
  await openBoard(board, boards, "Reporting");
  await openPage(app, `/app/${org.slug}/${path}`);
  await app.locator("h1").first().waitFor();
  await app.evaluate(() => document.fonts.ready);
  return { board, app };
}

for (const viewport of VIEWPORTS) {
  test(`Reporting matches Reporting, ${viewport.name}`, async ({ browser }) => {
    const { board, app } = await pages(browser, viewport, "reporting");
    await board.addStyleTag({ content: `${SPACING}.page>.note,.page>details.fold{display:none!important}.row .meta{visibility:hidden}` });
    await app.addStyleTag({ content: `main a .font-normal{visibility:hidden}` });
    await app.waitForLoadState("networkidle");
    await app.mouse.move(0, 0);
    const s = await compareRegion({ browser, boardPage: board, appPage: app, board: "Reporting", tab: `exams-${viewport.name}`, viewport: viewport.name, boardRegion: ".page", appRegion: APP_PAGE });
    console.log(`Reporting ${viewport.name}: ${s.percent}% largest ${JSON.stringify(s.largest)} | ${s.files.side}`);
    expect.soft(s.pass, `${viewport.name}: ${s.percent}% differs, see ${s.files.side}`).toBe(true);
  });
}
