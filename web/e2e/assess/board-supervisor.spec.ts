/**
 * Home, Supervisor home (docs/institution-overhaul/boards/SupervisorHome.dc.html) against the app, for a supervisor
 * ("Dr Patel") who leads circuits in the seeded organisation (support/seed-home.ts).
 * Run: E2E_REUSE_SERVER=1 VERIFY_WEB_URL=http://localhost:3114 npx playwright test e2e/assess/board-supervisor.spec.ts --output=test-results-home
 *
 * Compared region: the page content (the board's `.page`, the app's "Supervisor home" section); the sidebar is the
 * app shell, and the running, coming-up and recent lists sit under the section (nothing is removed).
 * Named exceptions: (1) spacing per DESIGN.md "Spacing rhythm and quiet selection" (24px rows, 1px light selection
 * borders); (2) rows beyond the board's 3 and 2 are hidden (the seeded supervisor leads more circuits); (2b) the board's sample words (the count in the title, the stations' names and counts) differ from the
 * seeded rows, so the layout is compared; (3) the board's design notes and build spec are display:none; (4) phone
 * dialogs are bottom sheets (none on this board).
 */
import { expect, test, type Browser, type Page } from "@playwright/test";
import { compareRegion, openBoard, serveBoards, type BoardServer } from "../support/board-diff";
import { openPage, signedInAs } from "../support/session";
import { seedHomeOrg, type HomeOrg } from "../support/seed-home";

const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1100 },
  { name: "mobile", width: 760, height: 1100 },
] as const;
const APP_PAGE = `section[aria-label="Supervisor home"]`;

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
  await signedInAs(appContext, org.supervisor);
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
  await openBoard(board, boards, "SupervisorHome");
  await openPage(app, `/app/${org.slug}/dashboard`);
  await app.getByRole("heading", { name: "Circuits you lead" }).waitFor();
  await app.evaluate(() => document.fonts.ready);
  return { board, app };
}

test("Supervisor home keeps the words the journeys read", async ({ browser }) => {
  const { app } = await pages(browser, VIEWPORTS[0]);
  await expect(app.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(app.getByRole("heading", { name: "Stations to review", exact: true }).first()).toBeVisible();
  await expect(app.getByRole("heading", { name: "Circuits you lead" })).toBeVisible();
  await expect(app.getByRole("link", { name: "All sittings" }).first()).toBeVisible();
});

for (const viewport of VIEWPORTS) {
  test(`Supervisor home matches the board, ${viewport.name}`, async ({ browser }) => {
    const { board, app } = await pages(browser, viewport);
    await board.addStyleTag({ content: `.page~*,div:has(>details.fold){display:none!important}` });
    await app.waitForLoadState("networkidle");
    // The seeded supervisor leads more circuits than the board's sample lists; rows beyond its 3 and 2 are hidden.
    await app.evaluate(() => {
      const keep: Record<string, number> = { "Stations to review": 4, "Circuits you lead": 3 };
      for (const h of document.querySelectorAll("h2")) {
        const limit = keep[h.textContent ?? ""];
        if (limit) [...(h.closest("section")?.children ?? [])].slice(limit).forEach((row) => ((row as HTMLElement).style.display = "none"));
      }
    });
    await app.mouse.move(0, 0);
    const s = await compareRegion({ browser, boardPage: board, appPage: app, board: "SupervisorHome", tab: `supervisor-${viewport.name}`, viewport: viewport.name, boardRegion: ".page", appRegion: APP_PAGE });
    console.log(`Supervisor home ${viewport.name}: ${s.percent}% largest ${JSON.stringify(s.largest)} | ${s.files.side}`);
    // (5) On a phone the two seeded "Every review done..." rows wrap to two lines where the board's drafts row is one
    // (the api cannot seed the board's drafts), which shifts everything below by 20px: 12% allowed there, 10% on desktop.
    const limit = viewport.name === "mobile" ? 12 : 10;
    expect.soft(s.percent, `${viewport.name}: ${s.percent}% differs, see ${s.files.side}`).toBeLessThan(limit);
  });
}
