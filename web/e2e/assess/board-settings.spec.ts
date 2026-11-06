import { expect, test, type Browser, type Page } from "@playwright/test";
import { compareRegion, openBoard, serveBoards, styleDifferences, type BoardServer, type StyleCheck } from "../support/board-diff";
import { openPage, signedInAs } from "../support/session";
import { seedPeopleOrg, type PeopleOrg } from "../support/seed-people";
import { seedScimTokens } from "../support/seed-settings";

/**
 * Settings (docs/institution-overhaul/boards/Settings.dc.html) against the app.
 * Run: E2E_REUSE_SERVER=1 VERIFY_WEB_URL=http://localhost:3109 npx playwright test e2e/assess/board-settings.spec.ts
 * PNGs and scores.json land in docs/institution-overhaul/verify/board-diff/.
 *
 * Compared region: the page content (the board's `.page` without its design notes, the app's Settings column); the
 * sidebar is the app shell. Tabs: Organisation, Single sign-on, Provisioning, Your account, Preferences, Invoices.
 *
 * Named exceptions:
 *  1. Spacing (user feedback 2026-11-05, DESIGN.md "Spacing rhythm and quiet selection"): the board's own css is
 *     loosened (rows 16px, padded cards 24px with a 16px gap) so layout is compared like for like; selection and focus
 *     are light blue 1px, never the board's saturated blue.
 *  2. Web address. The board shows /stmarys; the seeded organisation's slug is unique per run. Input text hidden both sides.
 *  3. The board draws alternatives side by side ("the three states above are alternatives"); the app shows the one
 *     that is true. Sign-in: Not connected / Two-step not required. Board rows for the other states are removed by their text (and the count left is asserted).
 *  4. Provisioning: the board's one-time token alert holds a made-up token and two connectors. The alert is
 *     display:none on the board (the app shows it only when a token has just been made, and none has); the board's
 *     row lines ("scim_9f2c… · last used 4 Nov") are visibility:hidden on the board. The app's own lines (the real
 *     prefix and last-used date) are NOT hidden, so their text counts against the score; the Okta trial token is seeded revoked.
 *  5. Your account and Preferences are the shared account capability (capabilities/account, access-owner). Preferences is
 *     scored (person data, timers, hidden both sides). Your account is scored: on an organisation surface its cards are the
 *     board's (capabilities/account/settings/AccountKit.tsx); the trainee surface keeps its Panels. The board draws two-factor
 *     off and on together, so the "Enabled" row and its note are removed on the board (the app shows the one that is true).
 *     The "Exam type" row (trainee practice exam) is not drawn on an organisation surface while no exam is chosen.
 *  6. The board's design-only notes (.note, build spec) are display:none.
 *  7. Invoices is a link card ("Open invoices") with no invoice data, so no invoices are seeded for this tab; its lead
 *     names the organisation ("St Mary's" on the board, "St Mary's Medical School" in the app), so the lead is
 *     visibility:hidden both sides. The invoice rows are scored in board-invoices.spec.ts.
 */
const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1100 },
  { name: "mobile", width: 760, height: 1100 },
] as const;
const APP_PAGE = `xpath=(//h1/ancestor::*[.//*[@role="tablist"]])[last()]`;

let boards: BoardServer;
let org: PeopleOrg;

test.beforeAll(async () => {
  test.setTimeout(300_000);
  boards = await serveBoards();
  org = await seedPeopleOrg();
  await seedScimTokens(org);
});
test.afterAll(async () => boards?.close());

const SPACING = `.row{padding-top:16px!important;padding-bottom:16px!important}.card.pad{padding:24px!important;gap:16px!important}.fields>div+div,.card.pad>div:has(>label)+div:has(>label){margin-top:12px}label{margin-bottom:8px!important}`;
const HIDE_BOARD = `${SPACING}
.page>.note,.page>details.fold{display:none!important}`;

async function pages(browser: Browser, viewport: { width: number; height: number }, path = "settings"): Promise<{ board: Page; app: Page }> {
  viewport = { ...viewport, height: 1700 };
  const boardContext = await browser.newContext({ viewport });
  const appContext = await browser.newContext({ viewport });
  await signedInAs(appContext, org.account);
  const board = await boardContext.newPage();
  const app = await appContext.newPage();
  await openBoard(board, boards, "Settings");
  await openPage(app, `/app/${org.slug}/${path}`);
  await app.getByRole("tablist").first().waitFor();
  await app.evaluate(() => document.fonts.ready);
  await board.addStyleTag({ content: HIDE_BOARD });
  return { board, app };
}

interface TabSpec {
  key: string;
  label: string;
  hideBoard: string;
  hideApp: string;
  /** Board rows removed by their text (the board draws alternatives side by side). */
  dropBoardText?: string[];
  /** How many `.card.pad > .row` the board has once those are removed. */
  boardRowsAfterDrop?: number;
}
const TABS: TabSpec[] = [
  { key: "organisation", label: "Organisation", hideBoard: "input.input{color:transparent!important}", hideApp: "input{color:transparent!important}" },
  {
    key: "sso",
    label: "Single sign-on",
    // Exception 3: only the true state shows (not connected; two-step not required). The other rows are removed by
    // their text below (one way only); the caption saying they are alternatives is hidden.
    hideBoard: ".card.pad>.meta:last-child{display:none!important}",
    hideApp: "",
    dropBoardText: ["Everyone signs in with", "It is set up but switched off", "Staff must confirm a code"],
    // One row in each of the two cards is left.
    boardRowsAfterDrop: 2,
  },
  {
    key: "provisioning",
    label: "Provisioning",
    // Exception 4.
    hideBoard: ".al.warn,.card.pad>.meta:last-child{display:none!important}.card .row .meta{visibility:hidden}.row .chip{visibility:visible}",
    hideApp: "",
  },
  {
    key: "account",
    label: "Your account",
    // Exception 5: the board draws two-factor off and on together; the app shows the true state (off, "Set up").
    hideBoard: "input.input,.av,.card.pad .row b{color:transparent!important}.av{visibility:hidden}.card.pad>.meta:last-child{display:none!important}",
    hideApp: "input{color:transparent!important}",
    dropBoardText: ["recovery codes left"],
  },
  { key: "preferences", label: "Preferences", hideBoard: ".row .meta{visibility:hidden}.card.pad>.meta:last-child{display:none!important}", hideApp: "" },
  { key: "invoices", label: "Invoices", hideBoard: ".card.pad>.meta{visibility:hidden}", hideApp: "main section p{visibility:hidden}" },
];

for (const tab of TABS) {
  for (const viewport of VIEWPORTS) {
    test(`Settings ${tab.label} matches Settings, ${viewport.name}`, async ({ browser }) => {
      const { board, app } = await pages(browser, viewport);
      if (tab.hideBoard) await board.addStyleTag({ content: tab.hideBoard });
      await board.locator(".tab", { hasText: new RegExp(`^${tab.label}$`) }).click();
      for (const text of tab.dropBoardText ?? []) await board.locator(".card.pad > .row", { hasText: text }).evaluateAll((rows) => rows.forEach((r) => r.remove()));
      if (tab.boardRowsAfterDrop !== undefined) expect(await board.locator(".card.pad > .row").count()).toBe(tab.boardRowsAfterDrop);
      if (tab.hideApp) await app.addStyleTag({ content: tab.hideApp });
      await app.getByRole("tab", { name: tab.label }).click();
      await app.waitForLoadState("networkidle");
      await app.mouse.move(0, 0);
      await board.mouse.move(0, 0);
      const s = await compareRegion({ browser, boardPage: board, appPage: app, board: "Settings", tab: `${tab.key}-${viewport.name}`, viewport: viewport.name, boardRegion: ".page", appRegion: APP_PAGE });
      console.log(`Settings ${tab.key} ${viewport.name}: ${s.percent}% largest ${JSON.stringify(s.largest)} | ${s.files.side}`);
      expect.soft(s.pass, `${tab.key} ${viewport.name}: ${s.percent}% differs, see ${s.files.side}`).toBe(true);
    });
  }
}

const TEXT = ["fontFamily", "fontSize", "fontWeight", "color"];
const STYLE_CHECKS: StyleCheck[] = [
  { name: "h1", board: "h1", app: "h1", props: [...TEXT, "lineHeight"] },
  { name: "active tab", board: ".tab.on", app: '[role="tab"][aria-selected="true"]', props: [...TEXT, "backgroundColor", "height"] },
  { name: "card title", board: ".card.pad h2", app: "main section h2 >> nth=0", props: [...TEXT, "lineHeight"] },
  { name: "chip", board: ".card.pad .chip", app: "main span.rounded-full >> nth=0", props: [...TEXT, "backgroundColor", "height"] },
];

test("Settings computed styles match Settings (SSO tab, desktop)", async ({ browser }) => {
  const { board, app } = await pages(browser, VIEWPORTS[0]);
  await board.locator(".tab", { hasText: /^Single sign-on$/ }).click();
  await app.getByRole("tab", { name: "Single sign-on" }).click();
  await app.locator("main h2").first().waitFor();
  expect(await styleDifferences(board, app, STYLE_CHECKS)).toEqual([]);
});
