import { expect, test } from "@playwright/test";
import { compareRegion, serveBoards, type BoardServer } from "../support/board-diff";
import { hideAnnotations, traineePages, VIEWPORTS } from "../support/board-trainee";
import { traineeOrg, type TraineeOrg } from "../support/seed-trainee";
import { openPage } from "../support/session";

/**
 * Trainee (docs/institution-overhaul/boards/Trainee.dc.html) against the app, as Amara Okoye. Run:
 * npx playwright test e2e/assess/board-trainee.spec.ts. PNGs and scores.json land in docs/institution-overhaul/verify/board-diff/.
 * Compared region: the board's `.page` and the app's `section[aria-label="My training"]`.
 * Named exceptions:
 *  - Tab strip, `.note` and the build-spec fold are the board's own annotations, hidden on the board side.
 *  - Tabs 2 and 4 to 8 (Practice history, Transcripts, Debriefs, Station record, Station runner, Practice sessions) are
 *    the transcripts, debrief, station-runner and practice-set capabilities (attempt-engine-owner / web-foundation-owner),
 *    mounted here but not drawn by domains/assess/trainee: not scored in this spec (see the report).
 *  - The hero's action is JoinRoom (clock chip and "Join"), the board's single "Go in" button: the journeys read /Join/.
 *  - Data: the board's March mock reads "1 of 6 stations completed" and a Year 3 date of 12 Nov; the seed has no finished
 *    station on a live circuit (no LiveKit) and the date is relative to the run.
 */
let boards: BoardServer;
let org: TraineeOrg;

test.beforeAll(async () => {
  test.setTimeout(900_000);
  boards = await serveBoards();
  org = await traineeOrg();
});
test.afterAll(async () => boards?.close());

for (const viewport of VIEWPORTS) {
  test(`Trainee home matches the board, ${viewport.name}`, async ({ browser }) => {
    const { board, app } = await traineePages(browser, boards, org, "Trainee", viewport, 0);
    await hideAnnotations(board);
    await openPage(app, `/app/${org.slug}/trainee`);
    await app.getByText("Your station is open").first().waitFor();
    await app.evaluate(() => document.fonts.ready);
    await app.mouse.move(0, 0);
    const tab = `tab-1-home-${viewport.name}`;
    const score = await compareRegion({ browser, boardPage: board, appPage: app, board: "Trainee", tab, viewport: viewport.name, boardRegion: ".page", appRegion: 'section[aria-label="My training"]' });
    console.log(`Trainee ${tab}: ${score.percent}% largest ${JSON.stringify(score.largest)} | ${score.files.side}`);
    expect.soft(score.pass, `${tab}: ${score.percent}%, see ${score.files.side}`).toBe(true);
  });
}
