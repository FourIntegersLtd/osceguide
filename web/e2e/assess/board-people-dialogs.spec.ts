import { expect, test, type Browser, type Page } from "@playwright/test";
import { call, orgPath } from "../support/api";
import { compareRegion, openBoard, serveBoards, type BoardServer } from "../support/board-diff";
import { openPage, signedInAs } from "../support/session";
import { addCohorts, addGroup, addr, addStaff, addTrainees, BOARD_FIVE, haveSignedIn, seedPeopleOrg, type PeopleOrg } from "../support/seed-people";

/**
 * The People dialogs (People.dc.html `d_*` states) against the app's dialogs, opened through the real buttons.
 * Run: E2E_REUSE_SERVER=1 npx playwright test e2e/assess/board-people-dialogs.spec.ts.
 *
 * Compared region: the dialog panel itself (board `.dlg`, app `[role="dialog"]`). Named exceptions, both sides:
 *  1. The heading and lead sentence name a person, group or address (the board's @stmarys.ac.uk, ours
 *     @stmarys.example.com), so their glyphs are transparent; the box, spacing, fields and buttons are compared.
 *  2. The members list: the board draws 48 people scrolled; the app seeds five. The list's glyphs are transparent, and the app's list is capped at three rows to match the board's three.
 *  3. Above the 10% bar by named cause, not by layout: sbulk (13.3%) because the board's
 *     lead sentence is shorter than ours (it names the held sittings), so its wrapped height differs; members (12.4%)
 *     because the board's rows wrap the address onto a second line (61px rows, 18px accent checkbox) where ours is
 *     one line (52px). Every other dialog is under 10% at 1440 and 760 (dcohort now 4.8%; PeopleDialog's title is 16px and its lead 14px at 1.5, as the board's `.dlg`).
 */
const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1100 },
  { name: "mobile", width: 760, height: 1100 },
] as const;
const HIDE = `.dlg h2,.dlg p,.dlg .meta{color:transparent!important}.dlg label.check span,.dlg ul *{color:transparent!important}`;
const HIDE_APP = `[role="dialog"] h2,[role="dialog"] p,[role="dialog"] ul *{color:transparent!important}[role="dialog"] ul li:nth-child(n+4){display:none}`;

interface Case { last?: boolean; key: string; tab: string; board: string; app: (p: Page) => Promise<void>; boardNth?: number; prep?: (p: Page) => Promise<void> }
const row = (p: Page, tid: string) => p.locator(`[data-testid="${tid}"]`);
const press = (p: Page, name: string, nth = 0) => p.getByRole("button", { name, exact: true }).nth(nth).click();
const tickTwo = async (p: Page, tid: string) => { await row(p, tid).nth(0).getByRole("checkbox").check(); await row(p, tid).nth(1).getByRole("checkbox").check(); };

const CASES: Case[] = [
  { key: "edit", tab: "Trainees", board: ".th + .row .btn.sm:text-is('Edit')", app: (p) => row(p, "trainee-row").nth(0).getByRole("button", { name: "Edit" }).click() },
  { key: "revoke", tab: "Trainees", board: ".th + .row .btn.sm:text-is('Revoke')", app: (p) => row(p, "trainee-row").nth(0).getByRole("button", { name: "Revoke" }).click() },
  { key: "restore", tab: "Trainees", board: ".btn.sm:text-is('Restore')", app: (p) => p.getByRole("button", { name: "Restore" }).first().click() },
  { key: "delete", tab: "Trainees", board: ".btn.sm.bad:text-is('Delete')", app: (p) => p.getByRole("button", { name: "Delete" }).first().click() },
  { key: "anon", tab: "Trainees", board: ".btn.sm:text-is('Anonymise')", app: (p) => p.getByRole("button", { name: "Anonymise" }).first().click() },
  { key: "bulkrevoke", tab: "Trainees", board: ".btn.sm.bad:text-is('Revoke access')", app: async (p) => { await tickTwo(p, "trainee-row"); await press(p, "Revoke access"); } },
  { key: "role", tab: "Staff", board: ".btn.sm:text-is('Change role')", app: (p) => row(p, "staff-row").nth(1).getByRole("button", { name: "Change role" }).click() },
  { key: "srevoke", tab: "Staff", board: ".btn.sm:text-is('Revoke')", last: true, app: (p) => row(p, "staff-row").nth(1).getByRole("button", { name: "Revoke", exact: true }).click() },
  { key: "srestore", tab: "Staff", board: ".btn.sm:text-is('Restore')", app: (p) => p.getByRole("button", { name: "Restore" }).first().click() },
  { key: "sbulk", tab: "Staff", board: ".btn.sm.bad:text-is('Revoke access')", app: async (p) => { await row(p, "staff-row").nth(1).getByRole("checkbox").check(); await press(p, "Revoke access"); } },
  { key: "rcohort", tab: "Groups and year groups", board: ".btn.sm:text-is('Rename')", app: (p) => press(p, "Rename", 0) },
  { key: "dcohort", tab: "Groups and year groups", board: ".btn.sm:text-is('Delete')", app: (p) => press(p, "Delete", 0) },
  { key: "rgroup", tab: "Groups and year groups", board: ".btn.sm:text-is('Rename') ", last: true, app: (p) => p.getByRole("button", { name: "Rename", exact: true }).last().click() },
  { key: "dgroup", tab: "Groups and year groups", board: ".btn.sm:text-is('Delete') ", last: true, app: (p) => p.getByRole("button", { name: "Delete", exact: true }).last().click() },
  { key: "members", tab: "Groups and year groups", board: ".btn.sm:text-is('People')", app: (p) => press(p, "People") },
];

let boards: BoardServer;
let org: PeopleOrg;

test.beforeAll(async () => {
  test.setTimeout(300_000);
  boards = await serveBoards();
  org = await seedPeopleOrg();
  const c = await addCohorts(org, [{ name: "Year 5", year: null }, { name: "Year 4", year: "2026/27" }]);
  const ids: Record<string, string> = {};
  for (const [i, p] of BOARD_FIVE.entries()) Object.assign(ids, await addTrainees(org, [{ ...p, cohort: i === 4 ? c["Year 4"] : i === 3 ? null : c["Year 5"] }]));
  haveSignedIn(BOARD_FIVE.map((p) => p.email));
  await call(org.token, orgPath(org.slug, `/trainees/${ids[BOARD_FIVE[4]!.email]}/access`), { method: "POST", body: { revoked: true } });
  await addGroup(org, "Tuesday rotation", Object.values(ids));
  const staff = await addStaff(org, [{ email: addr("patel"), role: "supervisor" }, { email: addr("clarke"), role: "supervisor" }, { email: addr("reid"), role: "admin" }]);
  haveSignedIn([addr("patel"), addr("reid")]);
  await call(org.token, orgPath(org.slug, `/memberships/${staff[addr("reid")]}/revoke`), { method: "POST" });
});
test.afterAll(async () => boards?.close());

async function pages(browser: Browser, viewport: { width: number; height: number }): Promise<{ board: Page; app: Page }> {
  const boardContext = await browser.newContext({ viewport });
  const appContext = await browser.newContext({ viewport });
  await signedInAs(appContext, org.account);
  const board = await boardContext.newPage();
  const app = await appContext.newPage();
  await openBoard(board, boards, "People");
  await openPage(app, `/app/${org.slug}/trainees`);
  await app.locator('[data-testid="people-page"]').waitFor();
  await app.evaluate(() => document.fonts.ready);
  return { board, app };
}

for (const c of CASES) {
  for (const viewport of VIEWPORTS) {
    test(`dialog ${c.key} matches People, ${viewport.name}`, async ({ browser }) => {
      const { board, app } = await pages(browser, viewport);
      await board.locator(".tab", { hasText: new RegExp(`^${c.tab}$`) }).click();
      await app.getByRole("tab", { name: c.tab }).click();
      await app.waitForLoadState("networkidle");
      const visible = board.locator(c.board.trim()).filter({ visible: true });
      await (c.last ? visible.last() : visible.first()).dispatchEvent("click");
      await c.app(app);
      await app.locator('[role="dialog"]').waitFor();
      await board.addStyleTag({ content: HIDE });
      await app.addStyleTag({ content: HIDE_APP });
      await board.mouse.move(0, 0);
      await app.mouse.move(0, 0);
      const s = await compareRegion({ browser, boardPage: board, appPage: app, board: "People", tab: `dialog-${c.key}-${viewport.name}`, viewport: viewport.name, boardRegion: ".dlg", appRegion: '[role="dialog"]' });
      console.log(`People dialog ${c.key} ${viewport.name}: ${s.percent}% largest ${JSON.stringify(s.largest)} | ${s.files.side}`);
      expect.soft(s.pass, `dialog ${c.key} ${viewport.name}: ${s.percent}% differs, see ${s.files.side}`).toBe(true);
    });
  }
}

