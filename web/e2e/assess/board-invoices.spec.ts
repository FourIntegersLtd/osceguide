/**
 * Invoices (docs/institution-overhaul/boards/Invoices.dc.html) against the app: "All invoices" and "One invoice".
 * Run: E2E_REUSE_SERVER=1 VERIFY_WEB_URL=http://localhost:3109 npx playwright test e2e/assess/board-invoices.spec.ts
 *
 * Named exceptions: (1) spacing per DESIGN.md (rows 16px, padded cards 24px, label 8px above its control);
 * (2) the board's "Money: needs your review" alert, its state tabs, "Load more" (one page of data), the empty-state
 * caption and design notes are display:none; (3) the invoice number and dates are written with the db seam
 * (seed-settings.ts) because no route sets them.
 */
import { expect, test, type Browser, type Page } from "@playwright/test";
import { compareRegion, openBoard, serveBoards, type BoardServer } from "../support/board-diff";
import { openPage, signedInAs } from "../support/session";
import { seedPeopleOrg, type PeopleOrg } from "../support/seed-people";
import { seedInvoices } from "../support/seed-settings";

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
  await seedInvoices(org);
});
test.afterAll(async () => boards?.close());

async function pages(browser: Browser, viewport: { width: number; height: number }, path: string): Promise<{ board: Page; app: Page }> {
  const boardContext = await browser.newContext({ viewport });
  const appContext = await browser.newContext({ viewport });
  await signedInAs(appContext, org.account);
  const board = await boardContext.newPage();
  const app = await appContext.newPage();
  await openBoard(board, boards, "Invoices");
  await openPage(app, `/app/${org.slug}/${path}`);
  await app.locator("h1").first().waitFor();
  await app.evaluate(() => document.fonts.ready);
  return { board, app };
}

const HIDE = `${SPACING}.page>.note,.page>details.fold,.page>.al.warn,.page>.tabs,.page>.meta{display:none!important}.row[style*="justify-content:center"]{display:none!important}`;
const STATES = [
  { key: "list", tab: "All invoices" },
  { key: "invoice", tab: "One invoice" },
] as const;

for (const state of STATES) {
  for (const viewport of VIEWPORTS) {
    test(`Invoices ${state.tab} matches Invoices, ${viewport.name}`, async ({ browser }) => {
      const { board, app } = await pages(browser, viewport, "settings/invoices");
      await board.locator(".tab", { hasText: new RegExp(`^${state.tab}$`) }).click();
      if (state.key === "invoice") await app.getByRole("button", { name: "Open INV-2026-0142" }).click();
      await board.addStyleTag({ content: HIDE });
      await app.waitForLoadState("networkidle");
      await app.mouse.move(0, 0);
      const s = await compareRegion({ browser, boardPage: board, appPage: app, board: "Invoices", tab: `${state.key}-${viewport.name}`, viewport: viewport.name, boardRegion: ".page", appRegion: APP_PAGE });
      console.log(`Invoices ${state.key} ${viewport.name}: ${s.percent}% largest ${JSON.stringify(s.largest)} | ${s.files.side}`);
      expect.soft(s.pass, `${state.key} ${viewport.name}: ${s.percent}% differs, see ${s.files.side}`).toBe(true);
    });
  }
}
