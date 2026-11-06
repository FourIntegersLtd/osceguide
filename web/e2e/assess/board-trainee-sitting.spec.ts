import { expect, test } from "@playwright/test";
import { compareRegion, serveBoards, type BoardServer } from "../support/board-diff";
import { hideAnnotations, traineePages, VIEWPORTS } from "../support/board-trainee";
import { traineeOrg, type TraineeOrg } from "../support/seed-trainee";
import { openPage } from "../support/session";

/**
 * TraineeSitting (docs/institution-overhaul/boards/TraineeSitting.dc.html) against the app. Run:
 * npx playwright test e2e/assess/board-trainee-sitting.spec.ts. PNGs and scores.json land in docs/institution-overhaul/verify/board-diff/.
 * Compared region: the board's `.page` and the app's `section[aria-label="Your sitting"]`.
 * Tabs scored: 0 Before it opens (Ben, Winter mock), 1 Station open (Amara, March mock), 2 Finished (Amara, Year 4 mock).
 * Named exceptions:
 *  - Tab strip, `.note` and the build-spec fold are the board's annotations, hidden on the board side.
 *  - Tabs 3 Joining (microphone denied and missing, Re-join) and 4 Join refusals need a blocked microphone and a refused
 *    join-token: not reachable with real data here, listed in the report and not scored.
 *  - These three tabs are STRUCTURAL, not scored passes (scores.json keeps the numbers): the board draws a Reading brief
 *    card, an "In the room" card (patient and microphone tiles) and a finished Station 1 beside a live Station 2, none of
 *    which exists without LiveKit and a marking engine locally, so the seed cannot give the page the board's content.
 *    Chrome (title, back link, hero, alert, chips, buttons) is what the restyle matched; the spec asserts title, back link
 *    and station rows.
 *  - Tab 5 Stations and result is a different card layout of the same rows as tab 2 in the board (no hero, rows inside
 *    a padded card); the app has one screen for both, so it is compared as tab 2.
 *  - The board draws three static stations of a Live March mock in every tab; the seed draws its own sittings (six
 *    stations on March and Winter, three on Year 4), and the hero's JoinRoom (clock chip and "Join") is the board's "Join".
 */
let boards: BoardServer;
let org: TraineeOrg;

test.beforeAll(async () => {
  test.setTimeout(900_000);
  boards = await serveBoards();
  org = await traineeOrg();
});
test.afterAll(async () => boards?.close());

const TABS = [
  { index: 0, key: "before-it-opens", person: 1, sitting: "winter", ready: "Before you start", title: "Winter mock", rows: 6 },
  { index: 1, key: "station-open", person: 0, sitting: "march", ready: "Your station is open", title: "March mock", rows: 6 },
  { index: 2, key: "finished", person: 0, sitting: "year4", ready: "Your result has been released", title: "Year 4 mock", rows: 3 },
] as const;

for (const viewport of VIEWPORTS) {
  for (const tab of TABS) {
    test(`TraineeSitting tab ${tab.index} ${tab.key} matches the board, ${viewport.name}`, async ({ browser }) => {
      const { board, app } = await traineePages(browser, boards, org, "TraineeSitting", viewport, tab.person);
      await board.locator(".tab").nth(tab.index).click();
      await hideAnnotations(board);
      await openPage(app, `/app/${org.slug}/trainee/sittings/${org.sittings[tab.sitting]}`);
      await app.getByText(tab.ready).first().waitFor();
      await app.evaluate(() => document.fonts.ready);
      await app.mouse.move(0, 0);
      const name = `tab-${tab.index + 1}-${tab.key}-${viewport.name}`;
      const score = await compareRegion({ browser, boardPage: board, appPage: app, board: "TraineeSitting", tab: name, viewport: viewport.name, boardRegion: ".page", appRegion: 'section[aria-label="Your sitting"]' });
      console.log(`TraineeSitting ${name}: ${score.percent}% largest ${JSON.stringify(score.largest)} | ${score.files.side}`);
      // Structural, not a pass: the score is recorded, the screen's chrome and rows are asserted (see the header).
      const page = app.locator('section[aria-label="Your sitting"]');
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(tab.title);
      await expect(page.getByText(/^Station \d+( ·|$)/)).toHaveCount(tab.rows);
      await expect(page.getByRole("link", { name: /All sittings/ })).toBeVisible();
    });
  }
}
