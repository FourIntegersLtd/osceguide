import { expect, test } from "@playwright/test";
import { serveBoards, type BoardServer } from "../support/board-diff";
import { scoreTab, VIEWPORTS, type TraineeTab } from "../support/board-trainee";
import { traineeOrg, type TraineeOrg } from "../support/seed-trainee";

/**
 * TraineeReview (docs/institution-overhaul/boards/TraineeReview.dc.html). Run: npx playwright test e2e/assess/board-trainee-review.spec.ts.
 * Compared region: the board's `.page` and the app's `section[aria-label="Station feedback"]`.
 * Tabs scored: 0 Ready (Amara, Year 4 station 1), 1 Not released (Ben, Year 4 station 1, decision a draft),
 * 2 Not marked (Amara, Year 4 station 3, which has no review).
 * Named exceptions:
 *  - Data: the board's station is "Chest pain history · March mock" and its ratings Green, Amber, Green; the seed's review
 *    has its own station titles and rating letters.
 */
let boards: BoardServer;
let org: TraineeOrg;
test.beforeAll(async () => {
  test.setTimeout(900_000);
  boards = await serveBoards();
  org = await traineeOrg();
});
test.afterAll(async () => boards?.close());

const slot = (person: number, n: number) => (o: TraineeOrg) => `/trainee/reviews/${o.year4Slots[person]?.[n]}`;
const TABS: TraineeTab[] = [
  { index: 0, key: "ready", person: 0, path: slot(0, 0), ready: "Overall" },
  { index: 1, key: "not-released", person: 1, path: slot(1, 0), ready: "Not released yet" },
  { index: 2, key: "not-marked", person: 0, path: slot(0, 2), ready: "Not marked yet" },
];

for (const viewport of VIEWPORTS) {
  for (const tab of TABS) {
    test(`TraineeReview tab ${tab.index} ${tab.key} matches the board, ${viewport.name}`, async ({ browser }) => {
      const { app, score } = await scoreTab(browser, boards, org, "TraineeReview", "Station feedback", tab, viewport);
      await expect(app.getByRole("heading", { level: 1, name: "Station feedback" })).toBeVisible();
      expect.soft(score.pass, `${score.percent}%, see ${score.files.side}`).toBe(true);
    });
  }
}
