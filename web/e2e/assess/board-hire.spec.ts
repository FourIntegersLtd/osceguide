/**
 * Hire overview (docs/institution-overhaul/boards/HireHome.dc.html) against the app, for the board's own state:
 * "Acme Health Trust" with 36 candidates, 4 assessors, 5 assessments, Band 6 nurse assessment day running and
 * 4 candidates waiting on a hiring decision (support/seed-hire.ts).
 * Run: E2E_REUSE_SERVER=1 VERIFY_WEB_URL=http://localhost:3113 npx playwright test e2e/assess/board-hire.spec.ts --output=test-results-hire
 *
 * Compared region: the page content (the board's `.page`, the app's dashboard column); the sidebar is the app shell.
 * Named exceptions: (1) spacing per DESIGN.md "Spacing rhythm and quiet selection" (24px rows, 1px light selection
 * borders); (2) the running circuit's live clock and its Open console button are real features the board does not
 * draw ("nothing that exists today may disappear"): the clock is hidden on the app side, the button stays;
 * (3) the board's design notes and build spec are display:none; (4) phone dialogs are bottom sheets (none on this board).
 */
import { expect, test, type Browser, type Page } from "@playwright/test";
import { compareRegion, openBoard, serveBoards, type BoardServer } from "../support/board-diff";
import { openPage, signedInAs } from "../support/session";
import { seedHireOrg } from "../support/seed-hire";
import type { SittingsOrg } from "../support/seed-sittings";

const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1100 },
  { name: "mobile", width: 760, height: 1100 },
] as const;
const APP_PAGE = `section[aria-label="Overview"]`;

let boards: BoardServer;
let org: SittingsOrg;

test.beforeAll(async () => {
  test.setTimeout(300_000);
  boards = await serveBoards();
  org = await seedHireOrg();
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
  await openBoard(board, boards, "HireHome");
  await openPage(app, `/app/${org.slug}/dashboard`);
  await app.getByRole("heading", { level: 1, name: "Overview" }).waitFor();
  await app.getByText("Needs your attention").waitFor();
  await app.evaluate(() => document.fonts.ready);
  return { board, app };
}

test("Hire overview keeps the words the journeys read", async ({ browser }) => {
  const { app } = await pages(browser, VIEWPORTS[0]);
  await expect(app.getByRole("heading", { level: 1 })).toHaveText("Overview");
  await expect(app.getByText("Acme Health Trust").first()).toBeVisible();
  await expect(app.getByText("4 candidates need a hiring decision")).toBeVisible();
  await expect(app.getByRole("link", { name: "Schedule an assessment" })).toBeVisible();
  await expect(app.getByText("Band 6 nurse assessment day").first()).toBeVisible();
});

for (const viewport of VIEWPORTS) {
  test(`Hire overview matches HireHome, ${viewport.name}`, async ({ browser }) => {
    const { board, app } = await pages(browser, viewport);
    await board.addStyleTag({ content: `.page>.note,.page>details.fold{display:none!important}` });
    await app.addStyleTag({ content: `[data-board-hide]{visibility:hidden!important}` });
    await app.waitForLoadState("networkidle");
    await app.mouse.move(0, 0);
    const s = await compareRegion({ browser, boardPage: board, appPage: app, board: "HireHome", tab: `overview-${viewport.name}`, viewport: viewport.name, boardRegion: ".page", appRegion: APP_PAGE });
    console.log(`HireHome ${viewport.name}: ${s.percent}% largest ${JSON.stringify(s.largest)} | ${s.files.side}`);
    expect.soft(s.pass, `${viewport.name}: ${s.percent}% differs, see ${s.files.side}`).toBe(true);
  });
}
