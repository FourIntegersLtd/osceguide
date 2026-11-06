/**
 * Run, Now running (docs/institution-overhaul/boards/LiveBoard.dc.html), tab "Now running", against the app's `/live`
 * for the seeded organisation of support/seed-home.ts (a circuit running, finished circuits earlier).
 * Run: E2E_REUSE_SERVER=1 VERIFY_WEB_URL=http://localhost:3114 npx playwright test e2e/assess/board-live-board.spec.ts --output=test-results-home
 *
 * Compared region: the page content (the board's `.page`, the app's "Now running" section); the sidebar is the app shell.
 * Named exceptions: (1) spacing per DESIGN.md "Spacing rhythm and quiet selection" (24px rows, 1px light selection
 * borders); (2) the board's tab strip, its two warnings that need a paused circuit with no recording (a circuit the
 * api cannot reach on demand) and its second Running row and "Show earlier" (the seeded history is one page) are hidden, as are the app's rows beyond the
 * board's; the sample words differ from the seeded rows, so the layout is compared; (3) the other tabs (connection,
 * Earlier, nothing running) are states of the same components and are asserted by words, not pixels; (4) the board's
 * design notes and build spec are display:none; (5) phone dialogs are bottom sheets (none on this board).
 */
import { expect, test, type Browser, type Page } from "@playwright/test";
import { compareRegion, openBoard, serveBoards, type BoardServer } from "../support/board-diff";
import { openPage, signedInAs } from "../support/session";
import { seedHomeOrg, type HomeOrg } from "../support/seed-home";

const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1100 },
  { name: "mobile", width: 760, height: 1100 },
] as const;
const APP_PAGE = `section[aria-label="Now running"]`;

let boards: BoardServer;
let org: HomeOrg;

test.beforeAll(async () => {
  test.setTimeout(400_000);
  boards = await serveBoards();
  org = await seedHomeOrg();
});
test.afterAll(async () => boards?.close());

async function pages(browser: Browser, viewport: { width: number; height: number }): Promise<{ board: Page; app: Page }> {
  const boardContext = await browser.newContext({ viewport });
  const appContext = await browser.newContext({ viewport });
  await signedInAs(appContext, org.account);
  await appContext.addInitScript(() => {
    localStorage.setItem("installPromptDismissed", "true");
    document.addEventListener("DOMContentLoaded", () => {
      const style = document.createElement("style");
      style.textContent = "nextjs-portal{display:none!important}";
      document.head.append(style);
    });
  });
  const board = await boardContext.newPage();
  const app = await appContext.newPage();
  await app.clock.setFixedTime(new Date("2026-11-05T14:00:00"));
  await openBoard(board, boards, "LiveBoard");
  await openPage(app, `/app/${org.slug}/live`);
  await app.getByRole("heading", { name: "Running", exact: true }).waitFor();
  await app.evaluate(() => document.fonts.ready);
  return { board, app };
}

test("Now running keeps the words the journeys read", async ({ browser }) => {
  const { app } = await pages(browser, VIEWPORTS[0]);
  await expect(app.getByRole("heading", { name: "Now running" })).toBeVisible();
  await expect(app.getByText("Trouble first, then least time left")).toBeVisible();
  await expect(app.getByRole("link", { name: /Open Circuit A/ })).toBeVisible();
  await expect(app.getByRole("region", { name: "Earlier" })).toBeVisible();
});

for (const viewport of VIEWPORTS) {
  test(`Now running matches the board, ${viewport.name}`, async ({ browser }) => {
    const { board, app } = await pages(browser, viewport);
    await board.addStyleTag({ content: `.page~*,details.fold,.note{display:none!important}` });
    await app.waitForLoadState("networkidle");
    await board.evaluate(() => {
      const hide = (el: Element | null | undefined) => el && ((el as HTMLElement).style.display = "none");
      hide(document.querySelector(".tabs"));
      const earlier = document.querySelectorAll(".page > .card:not(.fold)");
      hide(earlier[earlier.length - 1]?.lastElementChild);
      hide(document.querySelector(".al.bad"));
      hide(document.querySelectorAll(".page > .al.warn")[1]);
      const cards = document.querySelectorAll(".page > .card");
      hide(cards[0]?.querySelectorAll("a.row")[1]);
    });
    await app.evaluate(() => {
      const card = document.querySelector('section[aria-label="Running"]');
      [...(card?.children ?? [])].slice(2).forEach((row) => ((row as HTMLElement).style.display = "none"));
    });
    await app.mouse.move(0, 0);
    const s = await compareRegion({ browser, boardPage: board, appPage: app, board: "LiveBoard", tab: `live-${viewport.name}`, viewport: viewport.name, boardRegion: ".page", appRegion: APP_PAGE });
    console.log(`Now running ${viewport.name}: ${s.percent}% largest ${JSON.stringify(s.largest)} | ${s.files.side}`);
    // (6) On a phone the board's sample row is longer than the seeded one, so its clock wraps under the text and the
    // card is 25px taller: 12% allowed there, 10% on desktop.
    const limit = viewport.name === "mobile" ? 12 : 10;
    expect.soft(s.percent, `${viewport.name}: ${s.percent}% differs, see ${s.files.side}`).toBeLessThan(limit);
  });
}
