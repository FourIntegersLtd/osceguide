import { test, expect, type Browser, type Page } from "@playwright/test";
import { compareRegion, openBoard, serveBoards, type BoardServer } from "../support/board-diff";
import { openPage, signedInAs } from "../support/session";
import { addTrainees, BOARD_FIVE, seedPeopleOrg, type PeopleOrg } from "../support/seed-people";

/**
 * The People board's "Empty and error states" card (People.dc.html, sixth tab) against the app, one board card per
 * state. Run: E2E_REUSE_SERVER=1 npx playwright test e2e/assess/board-people-states.spec.ts.
 *
 * Compared: the board's `.g2 > .card:nth-child(k)` against the app's card for the same state. Named exceptions:
 *  - Card 2 (No staff yet): an organisation always has its owner on the staff list, so the state cannot be reached.
 *  - Card 5 (Supervisor, read only): needs a signed-in supervisor session; the app shows it as a warn Note above the tabs
 *    (covered by the access owner's role tests), not as a card.
 *  - Card 6 (warn and ok results about Dev Shah): each appears only after a real delete or anonymise of a person with a
 *    recorded decision, which needs a marked sitting; the Note component is the one Trainees already scores.
 *  - Scores (empty 13.2/13.3, no match 15.8/14.6, error 13.4/19.9 at 1440/760) sit above the 10% bar on crops about 100px
 *    tall: the app's card keeps the 24px padding and 16px gap the user asked for (ample, neat spacing) where the board
 *    uses 20px and 14px, so every line sits 2 to 4px lower. Text, colours, radius and borders match (see the side PNGs).
 *  - Card 4's error is forced by failing the panel's searched list request (route fulfil 500), as the api never fails on demand.
 */
const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1100 },
  { name: "mobile", width: 760, height: 1100 },
] as const;

let boards: BoardServer;
let empty: PeopleOrg;
let one: PeopleOrg;

test.beforeAll(async () => {
  test.setTimeout(240_000);
  boards = await serveBoards();
  empty = await seedPeopleOrg();
  one = await seedPeopleOrg();
  await addTrainees(one, [BOARD_FIVE[0]!]);
});
test.afterAll(async () => boards?.close());

async function pages(browser: Browser, org: PeopleOrg, viewport: { width: number; height: number }): Promise<{ board: Page; app: Page }> {
  const boardContext = await browser.newContext({ viewport });
  const appContext = await browser.newContext({ viewport });
  await signedInAs(appContext, org.account);
  const board = await boardContext.newPage();
  const app = await appContext.newPage();
  await openBoard(board, boards, "People");
  await board.locator(".tab:last-child").click();
  return { board, app };
}

const STATES = [
  {
    key: "empty", card: 1, org: () => empty,
    appCard: 'div:has(> h2:text-is("No trainees yet"))',
  },
  {
    key: "nomatch", card: 3, org: () => one,
    before: async (p: Page) => { await p.getByPlaceholder(/^Search /).first().fill("zz"); },
    appCard: 'div:has(> div:text-is("Search with no match"))',
  },
  {
    key: "error", card: 4, org: () => one,
    route: true,
    appCard: 'div:has(> [role="alert"])',
  },
] as const;

for (const s of STATES) {
  for (const viewport of VIEWPORTS) {
    test(`state ${s.key} matches People, ${viewport.name}`, async ({ browser }) => {
      const { board, app } = await pages(browser, s.org(), viewport);
      // The error is forced on the panel's own searched request, after the page has loaded, so the page keeps its data.
      if ("route" in s) await app.route(/\/trainees\?.*search=/, (r) => r.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "x" }) }));
      await openPage(app, `/app/${s.org().slug}/trainees`);
      if ("before" in s) await s.before(app);
      if ("route" in s) await app.getByPlaceholder(/^Search /).first().fill("zz");
      await app.locator(s.appCard).first().waitFor();
      await app.evaluate(() => document.fonts.ready);
      // The board lays six cards in two columns; the app's card is full width, so give it the board card's width.
      const width = await board.locator(`.g2 > .card:nth-child(${s.card})`).evaluate((el) => el.getBoundingClientRect().width);
      await app.locator(s.appCard).first().evaluate((el, w) => { el.style.width = `${w}px`; el.style.maxWidth = `${w}px`; }, width);
      await board.mouse.move(0, 0);
      await app.mouse.move(0, 0);
      const r = await compareRegion({ browser, boardPage: board, appPage: app, board: "People", tab: `state-${s.key}-${viewport.name}`, viewport: viewport.name, boardRegion: `.g2 > .card:nth-child(${s.card})`, appRegion: s.appCard });
      console.log(`People state ${s.key} ${viewport.name}: ${r.percent}% largest ${JSON.stringify(r.largest)} | ${r.files.side}`);
      expect.soft(r.pass, `state ${s.key} ${viewport.name}: ${r.percent}% differs, see ${r.files.side}`).toBe(true);
    });
  }
}

