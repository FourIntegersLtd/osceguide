import { expect, test, type Browser, type Page } from "@playwright/test";
import { compareRegion, openBoard, serveBoards, type BoardServer } from "../support/board-diff";
import { seedResultsOrg, type ResultsOrg } from "../support/seed-results";
import { openPage, signedInAs } from "../support/session";

/**
 * Results (docs/institution-overhaul/boards/Results.dc.html) against the app, for the seeded March mock, Year 4
 * mock and Year 3 training sitting. Run: npx playwright test e2e/assess/board-results.spec.ts.
 * Compared region: the board's `.page` and the app's `section[aria-label="Results"]`.
 * Named exceptions: `.note` and the build-spec fold are board annotations, hidden. The board's fourth tab
 * "Empty and long lists" is a state switch, hidden on the board side; its cards are compared structurally in
 * the unit tests (resultsIndex.test.ts). The board draws the same three rows under every tab, while the app filters
 * by tab (training never needs a decision), so tabs 1 and 2 compare the strip and the page only on "All".
 */
const PAGE = 'section[aria-label="Results"]';
const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1700 },
  { name: "mobile", width: 760, height: 1700 },
] as const;
const TABS = ["Needs a decision", "Ready to release", "All"] as const;

let boards: BoardServer;
let org: ResultsOrg;
test.beforeAll(async () => {
  test.setTimeout(600_000);
  boards = await serveBoards();
  org = await seedResultsOrg();
});
test.afterAll(async () => boards?.close());

async function pages(browser: Browser, viewport: { width: number; height: number }): Promise<{ board: Page; app: Page }> {
  const boardContext = await browser.newContext({ viewport });
  const appContext = await browser.newContext({ viewport });
  await signedInAs(appContext, org.account);
  const board = await boardContext.newPage();
  const app = await appContext.newPage();
  await openBoard(board, boards, "Results");
  await board.addStyleTag({ content: ".tab:nth-child(n+4),.note,details.fold{display:none!important}" });
  await openPage(app, `/app/${org.slug}/results`);
  await app.locator(`${PAGE} a[href*="/results"]`).first().waitFor();
  await app.evaluate(() => document.fonts.ready);
  return { board, app };
}

for (const viewport of VIEWPORTS) {
  test(`Results matches the board, every tab, ${viewport.name}`, async ({ browser }) => {
    const { board, app } = await pages(browser, viewport);
    for (const [index, label] of TABS.entries()) {
      await board.locator(".tab").nth(index).click();
      await app.getByRole("tab", { name: label, exact: true }).click();
      await board.mouse.move(0, 0);
      await app.mouse.move(0, 0);
      const tab = `tab-${index + 1}-${label.toLowerCase().replace(/ /g, "-")}-${viewport.name}`;
      const whole = index === TABS.length - 1;
      const score = await compareRegion({
        browser, boardPage: board, appPage: app, board: "Results", tab, viewport: viewport.name,
        boardRegion: whole ? ".page" : ".tabs", appRegion: whole ? PAGE : `${PAGE} [role="tablist"]`,
      });
      console.log(`Results ${tab}: ${score.percent}% largest ${JSON.stringify(score.largest)} | ${score.files.side}`);
      expect.soft(score.pass, `${tab}: ${score.percent}% differs, see ${score.files.side}`).toBe(true);
    }
  });
}
