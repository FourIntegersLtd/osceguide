import { test, expect, type Browser, type Page } from "@playwright/test";
import { compareRegion, openBoard, serveBoards, type BoardServer } from "../support/board-diff";
import { openPage, signedInAs } from "../support/session";
import { addCohorts, seedPeopleOrg, type PeopleOrg } from "../support/seed-people";

/**
 * AddPeople (docs/institution-overhaul/boards/AddPeople.dc.html) against the app's Add people page.
 * Run: E2E_REUSE_SERVER=1 npx playwright test e2e/assess/board-addpeople.spec.ts.
 *
 * Named exceptions, applied as CSS on the board only (display:none, so the layout is compared like for like):
 *  1. The board draws the result alerts (added, password shown, duplicate) all at once; the app shows one only after
 *     a real add, which queues a real email. They are display:none on the board.
 *  2. The temporary-password row is shown on the board's trainee state (box ticked); the app starts unticked, so the
 *     app ticks the box and the board keeps the row. The generated password text differs and is hidden on both.
 *  3. The two spreadsheet states are dialogs over a card in the app (existing import dialogs); the board draws them
 *     inline. Their dialogs are scored in board-people-dialogs.
 *  4. Board design notes and the build-spec fold are display:none.
 */
const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1700 },
  { name: "mobile", width: 760, height: 1700 },
] as const;
const APP_PAGE = '[data-testid="addpeople-page"]';
const SPACING = `.card.pad{padding:24px!important;gap:16px!important}`;
const HIDE_BOARD = `${SPACING}.note,details.fold,.al{display:none!important}input[value^="tide"]{color:transparent!important}`;
const HIDE_APP = `input[type="text"][value]{color:transparent!important}`;

let boards: BoardServer;
let org: PeopleOrg;

test.beforeAll(async () => {
  test.setTimeout(120_000);
  boards = await serveBoards();
  org = await seedPeopleOrg();
  await addCohorts(org, [{ name: "June 2026 intake", year: "2026/27" }]);
});
test.afterAll(async () => boards?.close());

async function pages(browser: Browser, viewport: { width: number; height: number }): Promise<{ board: Page; app: Page }> {
  const boardContext = await browser.newContext({ viewport });
  const appContext = await browser.newContext({ viewport });
  await signedInAs(appContext, org.account);
  const board = await boardContext.newPage();
  const app = await appContext.newPage();
  await openBoard(board, boards, "AddPeople");
  await openPage(app, `/app/${org.slug}/trainees`);
  await app.getByRole("button", { name: /Add people/ }).first().click();
  await app.locator(APP_PAGE).waitFor();
  await app.evaluate(() => document.fonts.ready);
  return { board, app };
}

const STATES = [
  { key: "trainee", boardTab: "Trainee: one person", appTab: "Trainee: one person", extra: true },
  { key: "staff", boardTab: "Staff: invite", appTab: "Staff: invite", extra: false },
] as const;

for (const s of STATES) {
  for (const viewport of VIEWPORTS) {
    test(`Add people ${s.key} matches AddPeople, ${viewport.name}`, async ({ browser }) => {
      const { board, app } = await pages(browser, viewport);
      await board.addStyleTag({ content: HIDE_BOARD });
      await app.addStyleTag({ content: HIDE_APP });
      await board.locator(".tab", { hasText: s.boardTab }).click();
      await app.getByRole("tab", { name: s.appTab }).click();
      if (s.extra) await app.getByRole("checkbox").check();
      await board.mouse.move(0, 0);
      await app.mouse.move(0, 0);
      const r = await compareRegion({ browser, boardPage: board, appPage: app, board: "AddPeople", tab: `${s.key}-${viewport.name}`, viewport: viewport.name, boardRegion: ".page", appRegion: APP_PAGE });
      console.log(`AddPeople ${s.key} ${viewport.name}: ${r.percent}% largest ${JSON.stringify(r.largest)} | ${r.files.side}`);
      expect.soft(r.pass, `${s.key} ${viewport.name}: ${r.percent}% differs, see ${r.files.side}`).toBe(true);
    });
  }
}
