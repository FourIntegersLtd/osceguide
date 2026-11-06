import { expect, test, type Browser, type Page } from "@playwright/test";
import { compareRegion, openBoard, serveBoards, type BoardServer } from "../support/board-diff";
import { seedConsoleWorld, type ConsoleWorld } from "../support/seed-console";
import { openPage, signedInAs } from "../support/session";

/**
 * Console states and dialogs (Console.dc.html tabs 7-8 and `d_help`, `d_add`; CircuitReview.dc.html) against the app.
 * Run: npx playwright test e2e/assess/board-console-states.spec.ts --grep "<case>". PNGs and scores.json: docs/institution-overhaul/verify/board-diff/.
 * Named exceptions:
 *  - Dialogs: the board's people and emails differ from the seed's (example.com); label text is transparent on both sides and the app list is capped at the board's two rows.
 *  - Log: the board lists nine actions with a named actor; the api returns the actor's id only, and nine kinds are not reachable
 *    without a voice room, so the app shows three and the board's rows 4-9 are hidden. The board draws the card with an h2; the app is a fold with a Hide toggle.
 *  - Circuit review: the board's two columns are wider than the app's side column, so the board region is set to the app's width.
 *  - Tabs 4, 5, 6, 9 (Badges and alerts, Listen in, Mark a finished station, Late arrivals refusals) are not scored: alerts, a live room and a
 *    refused append need a voice fault, a LiveKit room, or an exam circuit with Add trainee (not offered). See console-exceptions.md.
 */
const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1700 },
  { name: "mobile", width: 760, height: 1700 },
] as const;
const HIDE_DLG = ".dlg h2,.dlg p,.dlg label.check,.dlg .meta,.dlg .hint,.dlg li{color:transparent!important}";
const HIDE_DLG_APP = '[role="dialog"] h2,[role="dialog"] p,[role="dialog"] label,[role="dialog"] li,[role="dialog"] .mt-1\\.5{color:transparent!important}[role="dialog"] .max-h-64 > label:nth-child(n+3){display:none}';

let boards: BoardServer;
let w: ConsoleWorld;
test.beforeAll(async () => {
  test.setTimeout(900_000);
  boards = await serveBoards();
  w = await seedConsoleWorld();
});
test.afterAll(async () => boards?.close());

async function open(browser: Browser, viewport: { width: number; height: number }, boardName: string, circuit: string, tab: number | null): Promise<{ board: Page; app: Page }> {
  const boardContext = await browser.newContext({ viewport });
  const appContext = await browser.newContext({ viewport });
  await signedInAs(appContext, w.org.account);
  const board = await boardContext.newPage();
  const app = await appContext.newPage();
  await openBoard(board, boards, boardName);
  await board.addStyleTag({ content: ".tabs[role=tablist],.note,details.fold{display:none!important}" });
  await openPage(app, `/app/${w.org.slug}/circuits/${circuit}`);
  await app.locator('section[aria-label="Circuit console"]').getByRole("heading", { level: 1 }).first().waitFor();
  await app.evaluate(() => document.fonts.ready);
  if (tab !== null) await board.locator(".tabs[role=tablist] > button").nth(tab).dispatchEvent("click");
  return { board, app };
}

async function score(browser: Browser, p: { board: Page; app: Page }, board: string, tab: string, viewport: string, boardRegion: string, appRegion: string): Promise<void> {
  await p.board.mouse.move(0, 0);
  await p.app.mouse.move(0, 0);
  const s = await compareRegion({ browser, boardPage: p.board, appPage: p.app, board, tab, viewport, boardRegion, appRegion, mask: { board: [".clock"], app: ["[data-clock]"] } });
  console.log(`${board} ${tab} ${viewport}: ${s.percent}% largest ${JSON.stringify(s.largest)} | ${s.files.side}`);
  expect.soft(s.pass, `${tab} ${viewport}: ${s.percent}%`).toBe(true);
}

async function matchWidth(p: { board: Page; app: Page }, boardRegion: string, appRegion: string): Promise<void> {
  const width = await p.app.locator(appRegion).first().evaluate((el) => el.getBoundingClientRect().width);
  await p.board.locator(boardRegion).first().evaluate((el, x) => { (el as HTMLElement).style.width = `${x}px`; }, width);
}

for (const viewport of VIEWPORTS) {
  test(`help dialog matches Console, ${viewport.name}`, async ({ browser }) => {
    const p = await open(browser, viewport, "Console", w.live, null);
    await p.board.locator("button.help").dispatchEvent("click");
    await p.app.getByRole("button", { name: "Observing an examination" }).click();
    await p.app.locator('[role="dialog"]').waitFor();
    await p.board.addStyleTag({ content: ".dlg h2{color:inherit}" });
    await score(browser, p, "Console", `dialog-help-${viewport.name}`, viewport.name, ".dlg", '[role="dialog"]');
  });

  test(`add trainee dialog matches Console, ${viewport.name}`, async ({ browser }) => {
    const p = await open(browser, viewport, "Console", w.training, 1);
    await p.board.locator(".btn:text-is('Add trainee')").first().dispatchEvent("click");
    await p.app.getByRole("button", { name: "Add trainee" }).first().click();
    await p.app.locator('[role="dialog"]').waitFor();
    await p.app.locator('[role="dialog"] input[type="checkbox"]').first().waitFor();
    await p.board.addStyleTag({ content: HIDE_DLG });
    await p.app.addStyleTag({ content: HIDE_DLG_APP });
    await score(browser, p, "Console", `dialog-add-${viewport.name}`, viewport.name, ".dlg", '[role="dialog"]');
  });

  test(`changed by hand matches Console tab 8, ${viewport.name}`, async ({ browser }) => {
    const p = await open(browser, viewport, "Console", w.training, 7);
    await p.board.addStyleTag({ content: ".page > .card.pad > .row:nth-child(n+5),.page > .card.pad > .meta{display:none!important}" });
    await p.app.getByRole("button", { name: /What was changed by hand/ }).click();
    await p.app.getByText("Fire alarm test").first().waitFor();
    await p.app.addStyleTag({ content: '[data-board="station-content"]{display:none!important}' });
    const region = 'section:has(> button[aria-expanded="true"])';
    await matchWidth(p, ".page > .card.pad", region);
    await score(browser, p, "Console", `tab-8-changed-by-hand-${viewport.name}`, viewport.name, ".page > .card.pad", region);
  });

  test(`circuit review matches CircuitReview, ${viewport.name}`, async ({ browser }) => {
    const p = await open(browser, viewport, "CircuitReview", w.ended, null);
    await p.app.locator("#circuit-review").waitFor();
    const stations = "#circuit-review > div:nth-of-type(2)";
    await p.board.addStyleTag({ content: ".rail,.page > .card.pad:nth-of-type(1),.colm > .card.pad > .meta:last-child{display:none!important}" });
    await matchWidth(p, ".colm > .card:nth-child(1)", stations);
    await score(browser, p, "CircuitReview", `stations-to-mark-${viewport.name}`, viewport.name, ".colm > .card:nth-child(1)", stations);
    await matchWidth(p, ".colm > .card.pad", '[data-board="feedback"]');
    await score(browser, p, "CircuitReview", `feedback-${viewport.name}`, viewport.name, ".colm > .card.pad", '[data-board="feedback"]');
    await matchWidth(p, ".cola > .card.pad:nth-child(2)", "#circuit-review > div:last-child");
    await score(browser, p, "CircuitReview", `record-${viewport.name}`, viewport.name, ".cola > .card.pad:nth-child(2)", "#circuit-review > div:last-child");
  });
}
