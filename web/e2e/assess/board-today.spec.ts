/**
 * Home, Today (docs/institution-overhaul/boards/Today.dc.html) against the app, for the board's own state: an
 * administrator of "St Mary's Medical School" with a circuit running, decisions and results waiting, trainees who
 * have not joined and two sittings coming up (support/seed-home.ts).
 * Run: E2E_REUSE_SERVER=1 VERIFY_WEB_URL=http://localhost:3114 npx playwright test e2e/assess/board-today.spec.ts --output=test-results-home
 *
 * Compared region: the page content (the board's `.page`, the app's dashboard column); the sidebar is the app shell.
 * Named exceptions: (1) spacing per DESIGN.md "Spacing rhythm and quiet selection" (24px rows, 1px light selection
 * borders); (2) the board's sample words differ from the seeded rows where the api cannot reproduce them (the greeting
 * name, the running circuit's candidate line), so only the layout is compared there; (3) the board's design notes and
 * build spec are display:none; (4) phone dialogs are bottom sheets (none on this board); (5) rows beyond the board's two in Coming up are hidden (the seeded org also holds the results seed's sittings); (6) the running chip reads "Live" and keeps the phase in its title ("Live · Reading time" wraps the phone row; the phase is on the live board and the console); (7) the board's "06:12 left" is a fixed sample.
 */
import { expect, test, type Browser, type Page } from "@playwright/test";
import { compareRegion, openBoard, serveBoards, type BoardServer } from "../support/board-diff";
import { openPage, signedInAs } from "../support/session";
import { seedHomeOrg, type HomeOrg } from "../support/seed-home";

const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1100 },
  { name: "mobile", width: 760, height: 1100 },
] as const;
const APP_PAGE = `section[aria-label="Today"]`;

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
  await openBoard(board, boards, "Today");
  await openPage(app, `/app/${org.slug}/dashboard`);
  await app.getByText("Needs your attention").waitFor();
  await app.getByText("Coming up").waitFor();
  await app.evaluate(() => document.fonts.ready);
  return { board, app };
}

test("Today keeps the words the journeys read", async ({ browser }) => {
  const { app } = await pages(browser, VIEWPORTS[0]);
  await expect(app.getByRole("heading", { level: 1 })).toContainText("Good");
  await expect(app.getByRole("link", { name: "Schedule a sitting" })).toBeVisible();
  await expect(app.getByText("Running now").first()).toBeVisible();
  await expect(app.getByRole("link", { name: "Open console" })).toBeVisible();
  await expect(app.getByRole("link", { name: "All sittings" })).toBeVisible();
});

for (const viewport of VIEWPORTS) {
  test(`Today matches the board, ${viewport.name}`, async ({ browser }) => {
    const { board, app } = await pages(browser, viewport);
    await board.addStyleTag({ content: `.page~*,div:has(>details.fold){display:none!important}` });
    await app.waitForLoadState("networkidle");
    // The seeded org also carries the results seed's sittings; the board's sample lists two.
    await app.evaluate(() => {
      const head = [...document.querySelectorAll("h2")].find((h) => h.textContent === "Coming up");
      [...(head?.closest("section")?.children ?? [])].slice(3).forEach((row) => ((row as HTMLElement).style.display = "none"));
    });
    await app.mouse.move(0, 0);
    const s = await compareRegion({ browser, boardPage: board, appPage: app, board: "Today", tab: `today-${viewport.name}`, viewport: viewport.name, boardRegion: ".page", appRegion: APP_PAGE });
    console.log(`Today ${viewport.name}: ${s.percent}% largest ${JSON.stringify(s.largest)} | ${s.files.side}`);
    expect.soft(s.pass, `${viewport.name}: ${s.percent}% differs, see ${s.files.side}`).toBe(true);
  });
}
