import { expect, test, type Browser, type Page } from "@playwright/test";
import { call, orgPath } from "../support/api";
import { compareRegion, openBoard, serveBoards, styleDifferences, type BoardServer, type StyleCheck } from "../support/board-diff";
import { openPage, signedInAs } from "../support/session";
import {
  addCohorts, addGroup, addr, addStaff, addTrainees, BOARD_FIVE, fillers, haveSignedIn, seedPeopleOrg, unlinkAccount,
  type PeopleOrg,
} from "../support/seed-people";

/**
 * People (docs/institution-overhaul/boards/People.dc.html) against the app.
 * Run: E2E_REUSE_SERVER=1 npx playwright test e2e/assess/board-people.spec.ts. PNGs and scores.json land in
 * docs/institution-overhaul/verify/board-diff/.
 *
 * Compared region: the page content (the board's `.page` without its design notes, the app's People column). The
 * sidebar is the app shell, owned by its own board.
 *
 * Named exceptions on the Trainees tab, each because the board draws data the api cannot be given without a real
 * marked sitting or a real mailbox. The content is still rendered; only the glyphs are hidden (visibility:hidden,
 * so the layout is unchanged) on BOTH sides, never a mask box:
 *  1. Addresses. The board writes @stmarys.ac.uk. Seeding queues a real invitation email per address, so every
 *     seeded address is @stmarys.example.com (six characters longer). Email lines and the alert that quotes one are hidden.
 *  2. Programme names and stations sat. They derive from marked sittings ("Final-year OSCE", 6, 212 stations); a
 *     seeded organisation has none. The Programme and Sat columns and the hero's numbers are hidden.
 *  3. The "Booked" chip on Ben. It needs a scheduled sitting; his chip text is hidden.
 *  4. Rows 6 to 48. The board draws five of 48 and a Load more row; the app has the same Load more row, and rows
 *     6 and up (the other 20 loaded) are display:none in the app only.
 *  6. The board's sixth tab (Empty and error states, a design card) and its Load more row (the api page holds all 48) are display:none on the board.
 *  7. Exam access: the hero sentence names the organisation ("St Mary's Medical School" in the app, "St Mary's" on
 *     the board) and the Grant button is disabled (no exam to grant, none can be seeded) against the board's primary
 *     one; both are visibility:hidden on both sides. The app's "No practice access given yet" line (the board's grants table is hidden) is display:none.
 *  5. The board's two ticked-looking-but-unticked rows: the board says "2 selected" with both boxes empty, which the
 *     app cannot do. The app ticks Amara and Ben, so two 18px checkboxes differ.
 */
const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1100 },
  { name: "mobile", width: 760, height: 1100 },
] as const;
const APP_PAGE = '[data-testid="people-page"]';

let boards: BoardServer;
let org: PeopleOrg;

test.beforeAll(async () => {
  test.setTimeout(300_000);
  boards = await serveBoards();
  org = await seedPeopleOrg();
  const c = await addCohorts(org, [{ name: "Year 5", year: null }, { name: "Year 4", year: "2026/27" }]);
  const five = BOARD_FIVE.map((p, i) => ({ ...p, cohort: i === 4 ? c["Year 4"] : i === 3 ? null : c["Year 5"] }));
  // The api lists by created_at, id: one bulk call stamps every row alike and the id breaks the tie at
  // random, so the five go one call each, in the board's order, before the fillers.
  const ids: Record<string, string> = {};
  for (const person of five) Object.assign(ids, await addTrainees(org, [person]));
  Object.assign(ids, await addTrainees(org, fillers(43)));
  haveSignedIn([BOARD_FIVE[0]!, BOARD_FIVE[1]!, BOARD_FIVE[4]!, ...fillers(43)].map((p) => p.email));
  unlinkAccount(org.slug, BOARD_FIVE[3]!.email);
  await call(org.token, orgPath(org.slug, `/trainees/${ids[BOARD_FIVE[4]!.email]}/access`), { method: "POST", body: { revoked: true } });
  await addGroup(org, "Tuesday rotation", Object.values(ids).slice(0, 8));
  const staff = await addStaff(org, [
    { email: addr("patel"), role: "supervisor" }, { email: addr("clarke"), role: "supervisor" }, { email: addr("reid"), role: "admin" },
  ]);
  haveSignedIn([addr("patel"), addr("reid")]);
  await call(org.token, orgPath(org.slug, `/memberships/${staff[addr("reid")]}/revoke`), { method: "POST" });
});
test.afterAll(async () => boards?.close());

// User override (named exceptions 6 and 7, applied to the board's own css so layout is compared like for like):
// roomier spacing (rows 16px not 14px, padded cards 24px with a 16px gap) and a light blue 1px border where the
// board draws a saturated #1D4ED8 one (the selected-rows card).
const SPACING = `.row{padding-top:16px!important;padding-bottom:16px!important}.card.pad{padding:24px!important;gap:16px!important}
.card[style*="1D4ED8"]{border-color:#E8EFFC!important}`;
const HIDE_BOARD = `${SPACING}
.note,details.fold{display:none!important}
.tab:last-child{display:none!important}.card>.row:last-child:has(.btn:only-child){display:none!important}
.row .meta:not(:only-child),.row>div>.meta:nth-child(2){visibility:hidden}
.row>span:nth-of-type(2),.row>span:nth-of-type(3){visibility:hidden}
.al.ok{color:transparent!important}
.row:nth-of-type(3) .chip{visibility:hidden}`;
const HIDE_APP = `[data-testid="trainee-row"]:nth-child(n+7){display:none!important}
[data-testid="trainee-row"]>div>div:nth-child(2){visibility:hidden}
[data-testid="trainee-row"]>span:nth-of-type(2),[data-testid="trainee-row"]>span:nth-of-type(3){visibility:hidden}
[data-testid="people-page"] .bg-osce-success-bg{color:transparent!important}
[data-testid="trainee-row"]:nth-child(3) span.rounded-full{visibility:hidden}`;

async function pages(browser: Browser, viewport: { width: number; height: number }): Promise<{ board: Page; app: Page }> {
  viewport = { ...viewport, height: 1700 };
  const boardContext = await browser.newContext({ viewport });
  const appContext = await browser.newContext({ viewport });
  await signedInAs(appContext, org.account);
  const board = await boardContext.newPage();
  const app = await appContext.newPage();
  await openBoard(board, boards, "People");
  await openPage(app, `/app/${org.slug}/trainees`);
  await app.locator(APP_PAGE).waitFor();
  await app.evaluate(() => document.fonts.ready);
  return { board, app };
}

/** Put the app in the board's Trainees sample state: Chloe's invitation resent, two rows ticked. */
async function traineesState(app: Page): Promise<void> {
  const rows = app.locator('[data-testid="trainee-row"]');
  await rows.nth(0).waitFor();
  await expect(app.getByRole("button", { name: /Invite everyone not signed in on this page \(2\)/ })).toBeVisible();
  await rows.filter({ hasText: "Chloe Imran" }).getByRole("button", { name: "Resend invitation" }).click({ timeout: 8000 });
  await expect(app.locator(".bg-osce-success-bg").first()).toBeVisible();
  await rows.nth(0).getByRole("checkbox").check();
  await rows.nth(1).getByRole("checkbox").check();
}

for (const viewport of VIEWPORTS) {
  test(`Trainees matches People, ${viewport.name}`, async ({ browser }) => {
    const { board, app } = await pages(browser, viewport);
    await board.addStyleTag({ content: HIDE_BOARD });
    await app.addStyleTag({ content: HIDE_APP });
    await traineesState(app);
    await board.mouse.move(0, 0);
    await app.mouse.move(0, 0);
    const s = await compareRegion({ browser, boardPage: board, appPage: app, board: "People", tab: `trainees-${viewport.name}`, viewport: viewport.name, boardRegion: ".page", appRegion: APP_PAGE });
    console.log(`People trainees ${viewport.name}: ${s.percent}% largest ${JSON.stringify(s.largest)} | ${s.files.side}`);
    expect.soft(s.pass, `trainees ${viewport.name}: ${s.percent}% differs, largest ${JSON.stringify(s.largest)}, see ${s.files.side}`).toBe(true);
  });
}

const TEXT = ["fontFamily", "fontSize", "fontWeight", "color"];
const STYLE_CHECKS: StyleCheck[] = [
  { name: "h1", board: "h1", app: "h1", props: [...TEXT, "lineHeight"] },
  { name: "tabs", board: ".tabs", app: '[role="tablist"]', props: ["backgroundColor", "borderTopLeftRadius", "paddingTop", "columnGap", "height"] },
  { name: "active tab", board: ".tab.on", app: '[role="tab"][aria-selected="true"]', props: [...TEXT, "backgroundColor", "height"] },
  { name: "primary button", board: "a.btn.pri", app: 'button:has-text("Add people")', props: [...TEXT, "backgroundColor", "height", "borderTopLeftRadius"] },
  { name: "trainee row", board: ".th + .row", app: '[data-testid="trainee-row"] >> nth=0', props: [...TEXT, "paddingTop", "paddingLeft", "columnGap", "borderTopColor"] },
  { name: "small button", board: ".th + .row .btn.sm >> nth=0", app: '[data-testid="trainee-row"] button >> nth=0', props: [...TEXT, "height", "backgroundColor"] },
  { name: "chip", board: ".th + .row .chip >> nth=0", app: '[data-testid="trainee-row"] span.rounded-full >> nth=0', props: [...TEXT, "backgroundColor", "height"] },
  { name: "search", board: "input.input", app: 'input[type="search"]', props: [...TEXT, "height", "borderTopColor"] },
];

test("Trainees computed styles match People (desktop)", async ({ browser }) => {
  const { board, app } = await pages(browser, VIEWPORTS[0]);
  await board.addStyleTag({ content: SPACING });
  await app.locator('[data-testid="trainee-row"]').nth(0).waitFor();
  expect(await styleDifferences(board, app, STYLE_CHECKS)).toEqual([]);
});

test("Trainees hover states match People (desktop)", async ({ browser }) => {
  const { board, app } = await pages(browser, VIEWPORTS[0]);
  await app.locator('[data-testid="trainee-row"]').nth(0).waitFor();
  const hovers = [
    { tab: "hover-add-people", board: "a.btn.pri", app: 'button:has-text("Add people")' },
    { tab: "hover-row-button", board: ".th + .row .btn.sm >> nth=0", app: '[data-testid="trainee-row"] button >> nth=0' },
    { tab: "hover-invite-all", board: "button.btn >> nth=0", app: 'button:has-text("Invite everyone")' },
  ];
  for (const h of hovers) {
    await board.locator(h.board).hover();
    await app.locator(h.app).hover();
    const s = await compareRegion({ browser, boardPage: board, appPage: app, board: "People", tab: h.tab, viewport: "desktop", boardRegion: h.board, appRegion: h.app });
    console.log(`People ${h.tab}: ${s.percent}% largest ${JSON.stringify(s.largest)} | ${s.files.side}`);
    expect.soft(s.pass, `${h.tab}: ${s.percent}% differs, see ${s.files.side}`).toBe(true);
  }
});

const SWITCHED = [
  {
    key: "staff", label: "Staff", ready: '[data-testid="staff-row"] >> nth=3',
    checks: [
      { name: "staff row", board: ".th + .row", app: '[data-testid="staff-row"] >> nth=0', props: [...TEXT, "paddingTop", "paddingLeft", "columnGap", "borderTopColor"] },
      { name: "staff small button", board: ".row .btn.sm:text-is('Change role') >> nth=0", app: '[data-testid="staff-row"] button:text-is("Change role") >> nth=0', props: [...TEXT, "height", "backgroundColor"] },
      { name: "staff chip", board: ".row .chip:has-text('Active') >> nth=0", app: '[data-testid="staff-row"] span.rounded-full:has-text("Active") >> nth=0', props: [...TEXT, "backgroundColor", "height"] },
    ] satisfies StyleCheck[],
    hover: { tab: "hover-staff-button", board: ".row .btn.sm:text-is('Change role') >> nth=0", app: '[data-testid="staff-row"] button:text-is("Change role") >> nth=0' },
  },
  {
    key: "access", label: "Exam access", ready: 'form button[type="submit"]',
    checks: [
      { name: "grant button", board: ".card.pad .btn.pri", app: 'form button[type="submit"]', props: [...TEXT, "height", "backgroundColor", "borderTopLeftRadius"] },
    ] satisfies StyleCheck[],
    // No hover compare: the app's Grant button is disabled until the form is filled, the board's is drawn enabled.
    hover: null,
  },
] as const;

for (const tab of SWITCHED) {
  test(`${tab.label} computed styles and hover match People (desktop)`, async ({ browser }) => {
    const { board, app } = await pages(browser, VIEWPORTS[0]);
    await board.addStyleTag({ content: SPACING });
    await board.locator(".tab", { hasText: new RegExp(`^${tab.label}$`) }).click();
    await app.getByRole("tab", { name: tab.label }).click();
    await app.locator(tab.ready).first().waitFor();
    expect(await styleDifferences(board, app, tab.checks)).toEqual([]);
    if (!tab.hover) return;
    await board.locator(tab.hover.board).first().hover();
    await app.locator(tab.hover.app).first().hover();
    const s = await compareRegion({ browser, boardPage: board, appPage: app, board: "People", tab: tab.hover.tab, viewport: "desktop", boardRegion: tab.hover.board, appRegion: tab.hover.app });
    console.log(`People ${tab.hover.tab}: ${s.percent}% | ${s.files.side}`);
    expect.soft(s.pass, `${tab.hover.tab}: ${s.percent}% differs, see ${s.files.side}`).toBe(true);
  });
}

// ---- the other tabs. Named exceptions: addresses (see 1) are hidden on both sides; the audit wording differs
// because the app's text comes from the api; board-only notices that need a real action are display:none on the board.
const OTHER_TABS = [
  { key: "staff", label: "Staff", hideBoard: ".al.ok{display:none!important}.chip.info,.row>span:nth-of-type(1),.row>span:nth-of-type(2){visibility:hidden}", hideApp: '[data-testid="staff-row"]>span:nth-of-type(1),[data-testid="staff-row"]>span:nth-of-type(2){visibility:hidden}' },
  { key: "groups", label: "Groups and year groups", hideBoard: "", hideApp: "" },
  { key: "access", label: "Exam access", hideBoard: ".al.ok,.card:has(.th){display:none!important}.desc,.card.pad .btn.pri{visibility:hidden}", hideApp: '[data-testid="people-page"] p.text-assess-desc,[data-testid="people-page"] form button[type="submit"]{visibility:hidden}[data-testid="people-page"] p.text-assess-meta:last-child{display:none}' },
  { key: "history", label: "History", hideBoard: ".row *{visibility:hidden}", hideApp: '[data-testid="people-page"] div.items-baseline *{visibility:hidden}[data-testid="people-page"] div.items-baseline:nth-child(n+4){display:none!important}' },
] as const;

for (const tab of OTHER_TABS) {
  for (const viewport of VIEWPORTS) {
    test(`${tab.label} matches People, ${viewport.name}`, async ({ browser }) => {
      if (tab.key === "groups") await renameYear5();
      const { board, app } = await pages(browser, viewport);
      await board.addStyleTag({ content: `${SPACING}\n.page>.note,.page>.meta,.page>details.fold,.card.pad>.meta:last-child,.tab:last-child{display:none!important}\n${tab.hideBoard}` });
      if (tab.hideApp) await app.addStyleTag({ content: tab.hideApp });
      await board.locator(".tab", { hasText: new RegExp(`^${tab.label}$`) }).click();
      await app.getByRole("tab", { name: tab.label }).click();
      await app.waitForLoadState("networkidle");
      if (tab.key === "staff") {
        await app.locator('[data-testid="staff-row"]').nth(3).waitFor();
        await app.locator('[data-testid="staff-row"]').nth(1).getByRole("checkbox").check();
      }
      await board.mouse.move(0, 0);
      await app.mouse.move(0, 0);
      const s = await compareRegion({ browser, boardPage: board, appPage: app, board: "People", tab: `${tab.key}-${viewport.name}`, viewport: viewport.name, boardRegion: ".page", appRegion: APP_PAGE });
      console.log(`People ${tab.key} ${viewport.name}: ${s.percent}% largest ${JSON.stringify(s.largest)} | ${s.files.side}`);
      expect.soft(s.pass, `${tab.key} ${viewport.name}: ${s.percent}% differs, see ${s.files.side}`).toBe(true);
    });
  }
}

/** The board's Groups tab names its first year group "June 2026 intake"; the Trainees tab needs "Year 5". Rename after Trainees ran. */
async function renameYear5(): Promise<void> {
  const list = await call<{ items: { id: string; name: string }[] }>(org.token, orgPath(org.slug, `/cohorts`));
  const year5 = list.items.find((c) => c.name === "Year 5");
  if (year5) await call(org.token, orgPath(org.slug, `/cohorts/${year5.id}`), { method: "PATCH", body: { name: "June 2026 intake", academic_year: "2026/27" } });
}

