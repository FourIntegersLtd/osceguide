/**
 * Partner dashboard (docs/institution-overhaul/boards/Partner.dc.html) against the app: "Northern Deanery" with 1,240
 * link visits, 86 sign-ups and an estimated fee (support/seed-partner.ts). Tabs 1 to 4 (Overview, Performance, Your fee,
 * How we count) and 5 (Reporting) are diffed at 1440 and 760.
 * Run: E2E_REUSE_SERVER=1 VERIFY_WEB_URL=http://localhost:3114 npx playwright test e2e/assess/board-partner.spec.ts --output=test-results-partner
 *
 * Compared region: the page content (the board's `.page`, the app's `section[aria-label]`); the sidebar is the app shell.
 * Named exceptions: (1) spacing per DESIGN.md "Spacing rhythm and quiet selection"; (2) the board's tab strip is a switcher
 * between its seven screens and the app's is the four attribution tabs, so both strips are display:none in the diff and
 * the app's is checked by name below; (3) bars are drawn from the real daily series (the board's are seven fixed
 * heights), so their heights differ; (4) paid sign-ups (21 on the board) and the reference names are the api's (a non-pilot partner has none, so the reference list is hidden on both sides), not the
 * board's, and the seed has no payments; (5) Team (tab 6) is People's Staff screen, owned and diffed there; Custom dates
 * and errors (tab 7) are states, checked by words below, not a collage; (6) the board's notes and build spec are hidden;
 * (7) phone dialogs are bottom sheets (the Custom date range dialog is foundation Modal).
 */
import { expect, test, type Browser, type Page } from "@playwright/test";
import { compareRegion, openBoard, serveBoards, type BoardServer } from "../support/board-diff";
import { openPage, signedInAs } from "../support/session";
import { seedPartnerOrg } from "../support/seed-partner";

const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1100 },
  { name: "mobile", width: 760, height: 1100 },
] as const;
const TABS = [
  { key: "overview", board: 0, tab: "Overview", app: "dashboard", region: `section[aria-label="Partner dashboard"]`, ready: "How your links are performing" },
  { key: "performance", board: 1, tab: "Performance", app: "dashboard", region: `section[aria-label="Partner dashboard"]`, ready: "Link visits over time" },
  { key: "fee", board: 2, tab: "Your fee", app: "dashboard", region: `section[aria-label="Partner dashboard"]`, ready: "Estimated fee over time" },
  { key: "definitions", board: 3, tab: "How we count", app: "dashboard", region: `section[aria-label="Partner dashboard"]`, ready: "How we count your results" },
  { key: "reporting", board: 4, tab: "", app: "reporting", region: `section[aria-label="Reporting"]`, ready: "Tracking references" },
] as const;

let boards: BoardServer;
let org: Awaited<ReturnType<typeof seedPartnerOrg>>;

test.beforeAll(async () => {
  test.setTimeout(300_000);
  boards = await serveBoards();
  org = await seedPartnerOrg();
});
test.afterAll(async () => boards?.close());

async function pages(browser: Browser, viewport: { width: number; height: number }, spec: (typeof TABS)[number]): Promise<{ board: Page; app: Page }> {
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
  await openBoard(board, boards, "Partner");
  await board.locator(".tabs .tab").nth(spec.board).click();
  await openPage(app, `/app/${org.slug}/${spec.app}`);
  if (spec.tab) await app.getByRole("tab", { name: spec.tab }).click();
  await app.getByText(spec.ready).first().waitFor();
  await app.evaluate(() => document.fonts.ready);
  return { board, app };
}

test("Partner dashboard keeps the words the journeys read", async ({ browser }) => {
  const { app } = await pages(browser, VIEWPORTS[0], TABS[0]);
  await expect(app.getByRole("heading", { level: 1 })).toHaveText("Northern Deanery dashboard");
  await expect(app.getByRole("tablist", { name: "Partner dashboard sections" })).toBeVisible();
  for (const tab of ["Overview", "Performance", "Your fee", "How we count"]) await expect(app.getByRole("tab", { name: tab })).toBeVisible();
  await expect(app.getByLabel("Date range")).toBeVisible();
  await expect(app.getByLabel("Exam")).toBeVisible();
  await expect(app.getByText("Estimated fee (guide only)")).toBeVisible();
  await expect(app.getByText("per link visit.")).toBeVisible();
  await expect(app.getByText("Link visits", { exact: true }).first()).toBeVisible();
  await expect(app.getByText("£496", { exact: true })).toBeVisible();
  await app.getByLabel("Date range").selectOption("custom");
  await expect(app.getByRole("dialog", { name: "Custom date range" })).toBeVisible();
});

/** Fee, phone: the board draws seven weekly bars, the app the five real days of the month so far (exception 3). */
function maskFor(tab: string, viewport: string) {
  return tab === "fee" && viewport === "mobile" ? { board: ['.card.pad div[style*="height:140px"]'], app: ['[role="img"]'] } : undefined;
}

for (const viewport of VIEWPORTS) {
  for (const spec of TABS) {
    test(`Partner ${spec.key} matches Partner, ${viewport.name}`, async ({ browser }) => {
      const { board, app } = await pages(browser, viewport, spec);
      await board.addStyleTag({ content: `.tabs,.page>.note,.page>details.fold${spec.key === "reporting" ? ",.page>.head:first-child,.card.pad>.card,.card.pad>div.meta" : ""}{display:none!important}` });
      await app.addStyleTag({ content: `[data-board-hide]{display:none!important}` });
      await app.waitForLoadState("networkidle");
      await app.mouse.move(0, 0);
      const s = await compareRegion({ browser, boardPage: board, appPage: app, board: "Partner", tab: `${spec.key}-${viewport.name}`, viewport: viewport.name, boardRegion: ".page", appRegion: spec.region, mask: maskFor(spec.key, viewport.name) });
      console.log(`Partner ${spec.key} ${viewport.name}: ${s.percent}% largest ${JSON.stringify(s.largest)} | ${s.files.side}`);
      expect.soft(s.pass, `${spec.key} ${viewport.name}: ${s.percent}% differs, see ${s.files.side}`).toBe(true);
    });
  }
}
