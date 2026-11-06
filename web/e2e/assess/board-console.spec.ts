import { expect, test, type Browser, type Page } from "@playwright/test";
import { compareRegion, openBoard, serveBoards, type BoardServer } from "../support/board-diff";
import { seedConsoleWorld, type ConsoleWorld } from "../support/seed-console";
import { openPage, signedInAs } from "../support/session";

/**
 * Console (docs/institution-overhaul/boards/Console.dc.html) against the app. Run:
 * npx playwright test e2e/assess/board-console.spec.ts. PNGs and scores.json land in docs/institution-overhaul/verify/board-diff/.
 * Compared region: the board's `.page` (tab strip, annotation and build spec hidden) and the app's
 * `section[aria-label="Circuit console"]`; the sidebar is the app shell.
 * Named exceptions: see the README block at the end of docs/institution-overhaul/verify/board-diff/console-exceptions.md.
 *  - Live clock and "Left" cell are masked (a live server clock); station titles are the seed's "E2E library station N".
 */
const PAGE = 'section[aria-label="Circuit console"]';
const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1700 },
  { name: "mobile", width: 760, height: 1700 },
] as const;
const TABS = ["formal-exam", "training", "before-start-and-ended", "badges-and-alerts", "listen-in", "mark-a-finished-station", "circuit-feedback", "changed-by-hand", "late-arrivals-refusals"];
const HIDE = ".tabs[role=tablist],.note,.page > .al,.page > details.fold,.colm > .card:last-child";

let boards: BoardServer;
let w: ConsoleWorld;
test.beforeAll(async () => {
  test.setTimeout(900_000);
  boards = await serveBoards();
  w = await seedConsoleWorld();
});
test.afterAll(async () => boards?.close());

async function pages(browser: Browser, viewport: { width: number; height: number }, circuit: string): Promise<{ board: Page; app: Page }> {
  const boardContext = await browser.newContext({ viewport });
  const appContext = await browser.newContext({ viewport });
  await signedInAs(appContext, w.org.account);
  const board = await boardContext.newPage();
  const app = await appContext.newPage();
  await openBoard(board, boards, "Console");
  await board.addStyleTag({ content: `${HIDE}{display:none!important}` });
  await openPage(app, `/app/${w.org.slug}/circuits/${circuit}`);
  await app.addStyleTag({ content: '[data-board="station-content"],[data-board="alerts"]{display:none!important}' });
  await app.locator(PAGE).getByRole("heading", { level: 1 }).first().waitFor();
  await app.evaluate(() => document.fonts.ready);
  return { board, app };
}

const MASK = { board: [".clock", ".row span[style*='width:60px']"], app: ["[data-clock]"] };

for (const viewport of VIEWPORTS) {
  test(`Console tabs match the board, ${viewport.name}`, async ({ browser }) => {
    const live = await pages(browser, viewport, w.live);
    const training = await pages(browser, viewport, w.training);
    const fresh = await pages(browser, viewport, w.fresh);
    const ended = await pages(browser, viewport, w.ended);
    const plan: { index: number; pair: { board: Page; app: Page }; boardRegion: string; appRegion: string }[] = [
      { index: 0, pair: live, boardRegion: ".page", appRegion: PAGE },
      { index: 1, pair: training, boardRegion: ".page", appRegion: PAGE },
      { index: 2, pair: fresh, boardRegion: ".g2 > .card:nth-child(1)", appRegion: `${PAGE} [data-board="controls"]` },
      { index: 2, pair: ended, boardRegion: ".g2 > .card:nth-child(2)", appRegion: `${PAGE} [data-board="controls"]` },
    ];
    for (const step of plan) {
      await step.pair.board.locator(".tabs[role=tablist] > button").nth(step.index).dispatchEvent("click");
      await step.pair.board.mouse.move(0, 0);
      if (step.index === 2) {
        // Named exception: the board draws two states side by side in a half-width grid; the app shows one at its column width.
        const width = await step.pair.app.locator(step.appRegion).evaluate((el) => el.getBoundingClientRect().width);
        await step.pair.board.locator(step.boardRegion).evaluate((el, w) => { (el as HTMLElement).style.width = `${w}px`; }, width);
      }
      const tab = `tab-${step.index + 1}-${TABS[step.index]}${step.pair === fresh ? "-fresh" : step.pair === ended ? "-ended" : ""}-${viewport.name}`;
      const score = await compareRegion({ browser, boardPage: step.pair.board, appPage: step.pair.app, board: "Console", tab, viewport: viewport.name, boardRegion: step.boardRegion, appRegion: step.appRegion, mask: MASK });
      console.log(`Console ${tab}: ${score.percent}% | ${score.files.side}`);
      expect.soft(score.pass, `${tab}: ${score.percent}%`).toBe(true);
    }
  });
}
