import { expect, test } from "@playwright/test";
import { serveBoards, type BoardServer } from "../support/board-diff";
import { scoreTab, VIEWPORTS, type TraineeTab } from "../support/board-trainee";
import { traineeOrg, type TraineeOrg } from "../support/seed-trainee";

/**
 * SelfPractice (docs/institution-overhaul/boards/SelfPractice.dc.html). Run: npx playwright test e2e/assess/board-self-practice.spec.ts.
 * Compared region: the board's `.page` and the app's `section[aria-label="Self practice"]`.
 * Tab scored: 0 Screen (Amara). Named exceptions:
 *  - Tab 1 Not available is the screen for a workspace without the capability (a refusal page owned by the shell): not scored.
 *  - Data: the board lists three FINALS stations; the seed's org stations carry their own titles. The app keeps a "Past
 *    feedback" link and a count line ("N stations you can sit") the board does not draw; both stay (no feature is removed).
 */
let boards: BoardServer;
let org: TraineeOrg;
test.beforeAll(async () => {
  test.setTimeout(900_000);
  boards = await serveBoards();
  org = await traineeOrg();
});
test.afterAll(async () => boards?.close());

const TABS: TraineeTab[] = [{ index: 0, key: "screen", person: 0, path: () => "/trainee/practice", ready: "Nothing here is marked for the record." }];

for (const viewport of VIEWPORTS) {
  for (const tab of TABS) {
    test(`SelfPractice tab ${tab.index} ${tab.key} matches the board, ${viewport.name}`, async ({ browser }) => {
      const { app, score } = await scoreTab(browser, boards, org, "SelfPractice", "Self practice", tab, viewport);
      await expect(app.getByRole("heading", { level: 1, name: "Self practice" })).toBeVisible();
      expect.soft(score.pass, `${score.percent}%, see ${score.files.side}`).toBe(true);
    });
  }
}
