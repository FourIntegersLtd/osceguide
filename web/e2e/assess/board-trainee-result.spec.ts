import { expect, test } from "@playwright/test";
import { serveBoards, type BoardServer } from "../support/board-diff";
import { scoreTab, VIEWPORTS, type TraineeTab } from "../support/board-trainee";
import { traineeOrg, type TraineeOrg } from "../support/seed-trainee";

/**
 * TraineeResult (docs/institution-overhaul/boards/TraineeResult.dc.html). Run: npx playwright test e2e/assess/board-trainee-result.spec.ts.
 * Compared region: the board's `.page` and the app's `section[aria-label="Assessment outcome"]`.
 * Tabs scored: 0 Released (Amara, Year 4 mock), 1 Not released yet (Ben, Year 4 mock, decision still a draft).
 * Named exceptions:
 *  - Tab 2 Acknowledge draws a checkbox card and a "Hire" card the app does not have (the app acknowledges with the hero's
 *    "I have read this" button, and the recruitment outcome is simply never rendered): not scored, listed in the report.
 *  - Data: the board's Pass, 72.4 / 100 and its three stations; the seed's decision has its own score and three stations.
 */
let boards: BoardServer;
let org: TraineeOrg;
test.beforeAll(async () => {
  test.setTimeout(900_000);
  boards = await serveBoards();
  org = await traineeOrg();
});
test.afterAll(async () => boards?.close());

const TABS: TraineeTab[] = [
  { index: 0, key: "released", person: 0, path: (o) => `/trainee/results/${o.sittings.year4}`, ready: "I have read this" },
  { index: 1, key: "not-released", person: 1, path: (o) => `/trainee/results/${o.sittings.year4}`, ready: "Not released yet" },
];

for (const viewport of VIEWPORTS) {
  for (const tab of TABS) {
    test(`TraineeResult tab ${tab.index} ${tab.key} matches the board, ${viewport.name}`, async ({ browser }) => {
      const { app, score } = await scoreTab(browser, boards, org, "TraineeResult", "Assessment outcome", tab, viewport);
      await expect(app.getByRole("heading", { level: 1, name: "Assessment outcome" })).toBeVisible();
      expect.soft(score.pass, `${score.percent}%, see ${score.files.side}`).toBe(true);
    });
  }
}
