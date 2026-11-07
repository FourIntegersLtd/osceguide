import { expect, test, type Browser, type Page } from "@playwright/test";
import { compareRegion, openBoard, serveBoards, styleDifferences, type BoardServer, type StyleCheck } from "../support/board-diff";
import { seedSitting, seedSittingsOrg, type SittingsOrg } from "../support/seed-sittings";
import { openPage, signedInAs } from "../support/session";

/**
 * Sittings (docs/institution-overhaul/boards/Sittings.dc.html) against the app, for the board's own
 * four sittings. Run: npx playwright test e2e/assess/board-sittings.spec.ts. PNGs and scores.json land in
 * docs/institution-overhaul/verify/board-diff/.
 *
 * Compared region: the board's `.page` and the app's `section[aria-label="Sittings"]`; the sidebar is the app shell.
 * Named exceptions (none is a mask over app output):
 *  - The board's strip has seven labels; "Filters" and "Empty states" are the board's own page-state switches, not
 *    screens of the app, so they are hidden on the board side. The board also draws the same four rows under every
 *    status tab, while the app asks the server for that status; tabs 2 to 5 therefore compare the strip (with its
 *    active tab) and the rest of the page only on "All".
 *  - `.note` and the build-spec fold are the board's annotations, hidden on the board side.
 *  - Tab 6 "Filters" repeats Status/Kind/Exam/dates/search in a second card and a "Next up" card: it describes
 *    the server filters, whose controls are the tab strip and the filter card already compared on "All".
 *  - Tab 7 "Empty states": its first and third cards are compared with the app's empty and no-match states; the
 *    supervisor and hire cards are words about other roles and the hire vocabulary (covered by role-matrix specs).
 * - Computed styles: line-height "normal" (the board) against the app's pixel line heights, letter-spacing (-0.042px, the app's global tracking) and the board's tab strip and table head
 *   border colours (no border is drawn there) are not compared; the hero border is the light `--assess-select-border`
 *   where the board has a saturated blue, by the style brief ("1px light borders").
 * - Order: the api lists newest first, so the sittings are created in reverse of the board's row order.
 * - "Load more" is not drawn when the server has no further page; the board always draws it. Four sittings fit one page.
 * - Added after the board was drawn (the board shows neither, so they are hidden on the app side, as named exceptions):
 *   the "Show" preset strip (Everything / Upcoming / Waiting for decisions / Past), the "Next step" column and the
 *   exam-sittings footnote. They are covered by sittingList.test.ts. The "Status"
 *   strip is the board's tab strip.
 * Live clocks and avatars: none on this page, no mask.
 */
const PAGE = 'section[aria-label="Sittings"]';
const STATUS_STRIP = `${PAGE} [role="tablist"][aria-label="Status"]`;
const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1100 },
  { name: "mobile", width: 760, height: 1100 },
] as const;
const TABS = ["All", "Scheduled", "Running", "Finished", "Cancelled"] as const;

let boards: BoardServer;
let org: SittingsOrg;

function at(day: number, month: number, hour = 9): Date {
  return new Date(new Date().getFullYear(), month - 1, day, hour, 0);
}

test.beforeAll(async () => {
  test.setTimeout(600_000);
  boards = await serveBoards();
  org = await seedSittingsOrg({ adminName: "Dr Okafor", trainees: 24, supervisors: [] });
  const all = (n: number) => Array.from({ length: n }, (_, i) => i);
  const today = new Date();
  today.setHours(9, 0, 0, 0);
  await seedSitting(org, { name: "Paediatrics catch-up", mode: "exam", exam: "year4", scheduledFor: null, circuits: [] });
  await seedSitting(org, {
    name: "Summer finals", mode: "exam", exam: "finals", scheduledFor: at(26, 11),
    circuits: all(24).map((i) => ({ name: `Circuit ${i + 1}`, people: [i], supervisor: null, stations: 6 })),
  });
  await seedSitting(org, {
    name: "Year 3 practice round", mode: "training", exam: "year3", scheduledFor: at(12, 11),
    circuits: [0, 1].map((c) => ({ name: `Circuit ${c + 1}`, people: all(8).map((i) => c * 8 + i), supervisor: null, stations: 8 })),
  });
  await seedSitting(org, {
    name: "March mock", mode: "exam", exam: "finals", scheduledFor: today, start: true,
    circuits: all(8).map((i) => ({ name: `Circuit ${i + 1}`, people: [i], supervisor: null, stations: 6 })),
  });
});
test.afterAll(async () => boards?.close());

async function pages(browser: Browser, viewport: { width: number; height: number }): Promise<{ board: Page; app: Page }> {
  const boardContext = await browser.newContext({ viewport });
  const appContext = await browser.newContext({ viewport });
  await signedInAs(appContext, org.account);
  const board = await boardContext.newPage();
  const app = await appContext.newPage();
  await openBoard(board, boards, "Sittings");
  await board.addStyleTag({ content: ".tab:nth-child(n+6),.note,details.fold{display:none!important}" });
  // Named exception: the board always draws "Load more"; the app draws it only when the server has a further page.
  await board.addStyleTag({ content: ".row:has(> button.btn.sm){display:none!important}" });
  await openPage(app, `/app/${org.slug}/sittings`);
  await app.locator(`${PAGE} a[href*="/sittings/"]`).first().waitFor();
  await app.addStyleTag({ content: `${PAGE} [role="tablist"][aria-label="Show"],${PAGE} [data-column="next-step"],${PAGE} [data-footnote]{display:none!important}` });
  await app.evaluate(() => document.fonts.ready);
  return { board, app };
}

for (const viewport of VIEWPORTS) {
  test(`Sittings matches the board, every tab, ${viewport.name}`, async ({ browser }) => {
    const { board, app } = await pages(browser, viewport);
    for (const [index, label] of TABS.entries()) {
      await board.locator(".tab").nth(index).click();
      await app.locator(`${STATUS_STRIP}`).getByRole("tab", { name: label, exact: true }).click();
      await board.mouse.move(0, 0);
      await app.mouse.move(0, 0);
      const tab = `tab-${index + 1}-${label.toLowerCase()}-${viewport.name}`;
      if (index === 0) {
        await app.locator(`${PAGE} a[href*="/sittings/"]`).first().waitFor();
        const score = await compareRegion({ browser, boardPage: board, appPage: app, board: "Sittings", tab, viewport: viewport.name, boardRegion: ".page", appRegion: PAGE });
        console.log(`Sittings ${tab}: ${score.percent}% largest ${JSON.stringify(score.largest)} | ${score.files.side}`);
        expect.soft(score.pass, `${tab}: ${score.percent}% differs, largest ${JSON.stringify(score.largest)}, see ${score.files.side}`).toBe(true);
      } else {
        const score = await compareRegion({ browser, boardPage: board, appPage: app, board: "Sittings", tab, viewport: viewport.name, boardRegion: ".tabs", appRegion: `${STATUS_STRIP}` });
        console.log(`Sittings ${tab} (strip): ${score.percent}% | ${score.files.side}`);
        expect.soft(score.pass, `${tab}: strip ${score.percent}% differs, see ${score.files.side}`).toBe(true);
      }
    }
  });
}

const BOX = ["backgroundColor", "borderTopWidth", "borderTopColor", "borderTopLeftRadius", "paddingTop", "paddingRight", "paddingBottom", "paddingLeft", "rowGap", "columnGap", "width", "height"];
// Rows carry a status chip; the "Next up" hero link to a sitting does not.
const ROW = `${PAGE} a[href*="/sittings/"]:has(.rounded-full)`;
const STYLE_CHECKS: StyleCheck[] = [
  { name: "h1", board: "h1", app: "h1" },
  { name: "eyebrow", board: ".eyebrow", app: `${PAGE} > div:first-child .uppercase` },
  { name: "description", board: ".desc", app: `${PAGE} p` },
  { name: "schedule button", board: "a.btn.pri >> nth=0", app: `${PAGE} a[href$="/sittings/new"]` },
  { name: "hero", board: ".hero", app: `xpath=//section[@aria-label="Sittings"]/div[2]`, props: BOX },
  { name: "hero title", board: ".hero h2", app: `xpath=//section[@aria-label="Sittings"]/div[2]//h2` },
  { name: "tab strip", board: ".tabs", app: `${STATUS_STRIP}`, props: BOX },
  { name: "tab on", board: ".tab.on", app: `${STATUS_STRIP} [role="tab"][aria-selected="true"]` },
  { name: "tab off", board: ".tab:not(.on) >> nth=0", app: `${STATUS_STRIP} [role="tab"][aria-selected="false"] >> nth=0` },
  { name: "filter card", board: ".card.pad", app: `${PAGE} #sitting-kind >> xpath=ancestor::div[contains(@class,"rounded-panel")]`, props: BOX },
  { name: "filter label", board: "label", app: `${PAGE} label >> nth=0` },
  { name: "filter select", board: "select.input >> nth=0", app: "#sitting-kind" },
  { name: "filter date", board: "input[type=date] >> nth=0", app: "#sitting-from" },
  { name: "search input", board: "input.input[placeholder]", app: "#sitting-search" },
  { name: "clear filters", board: `xpath=//a[normalize-space()="Clear filters"]`, app: `${PAGE} button:has-text("Clear filters")` },
  { name: "table head", board: ".th", app: `xpath=//section[@aria-label="Sittings"]//span[normalize-space()="Kind"]/..`, props: BOX },
  { name: "row", board: "a.row >> nth=0", app: `${ROW} >> nth=0`, props: BOX },
    { name: "running chip", board: ".chip.live", app: `${ROW} >> nth=0 >> .rounded-full` },
  { name: "scheduled chip", board: ".chip.info >> nth=0", app: `${ROW} >> nth=1 >> .rounded-full` },
  { name: "needs-circuits chip", board: ".chip.warn", app: `${ROW} >> nth=3 >> .rounded-full` },
];

test("Sittings computed styles match the board (All, desktop)", async ({ browser }) => {
  const { board, app } = await pages(browser, VIEWPORTS[0]);
  // Named exceptions, each reasoned in the header: global tracking, undrawn borders, and the hero's light border.
  const exceptions = [/: letterSpacing /, /^tab strip: borderTopColor /, /^table head: borderTopColor /, /^hero: borderTopColor /, /: lineHeight board normal app \d+px$/];
  const differences = (await styleDifferences(board, app, STYLE_CHECKS)).filter((line) => !exceptions.some((rule) => rule.test(line)));
  expect(differences).toEqual([]);
});

test("Sittings hover states match the board (All, desktop)", async ({ browser }) => {
  const { board, app } = await pages(browser, VIEWPORTS[0]);
  const hovers = [
    { tab: "hover-schedule-button", board: "a.btn.pri >> nth=0", app: `${PAGE} a[href$="/sittings/new"]` },
    { tab: "hover-open-sitting", board: ".hero a.btn", app: `xpath=//section[@aria-label="Sittings"]/div[2]//a` },
    { tab: "hover-row", board: "a.row >> nth=1", app: `${ROW} >> nth=1` },
    { tab: "hover-tab", board: ".tab:not(.on) >> nth=0", app: `${STATUS_STRIP} [role="tab"][aria-selected="false"] >> nth=0` },
  ];
  for (const h of hovers) {
    await board.locator(h.board).hover();
    await app.locator(h.app).hover();
    const score = await compareRegion({ browser, boardPage: board, appPage: app, board: "Sittings", tab: h.tab, viewport: "desktop", boardRegion: h.board, appRegion: h.app });
    console.log(`Sittings ${h.tab}: ${score.percent}% | ${score.files.side}`);
    expect.soft(score.pass, `${h.tab}: ${score.percent}% differs, see ${score.files.side}`).toBe(true);
  }
});
