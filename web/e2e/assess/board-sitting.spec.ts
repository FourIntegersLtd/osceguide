import { expect, test, type Browser, type Page } from "@playwright/test";
import { compareRegion, openBoard, serveBoards, type BoardServer } from "../support/board-diff";
import { seedSitting, seedSittingsOrg, type SittingsOrg } from "../support/seed-sittings";
import { openPage, signedInAs } from "../support/session";

/**
 * Sitting detail (docs/institution-overhaul/boards/Sitting.dc.html) against the app, for the board's March mock:
 * Ms Clarke admin and supervisor of circuit 3, Dr Patel supervisor, cohort "Year 5", eight circuits of six stations.
 * Run: npx playwright test e2e/assess/board-sitting.spec.ts -g "<tab>". PNGs land in docs/institution-overhaul/verify/board-diff/.
 * Named exceptions:
 *  - The board's tabs 4 and 5 ("Primary action by step", "Other actions") are annotation states, not screens; the
 *    primary action per step is covered by sittingSteps tests. They are hidden on the board side.
 *  - The board sitting is "Today 09:00"; the sitting is seeded for today at 09:00 and not started, so it reads Scheduled.
 *  - The board draws three circuits and a "5 more circuits" note as its own sample abbreviation, so three circuits are
 *    seeded; the rail then reads "3 candidates assigned" where the board says 8.
 *  - The board titles a circuit "Circuit 1 · Amara Okoye" on the Circuits tab but "Circuit 1" on Candidates; the app shows the
 *    circuit's one stored name in both places, so the seeded name carries the person and the Candidates label differs.
 *  - Trainees use example.com emails with the board's display names.
 */
const PAGE = 'section[aria-label="Sitting"]';
const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1100 },
  { name: "mobile", width: 760, height: 1100 },
] as const;
const TABS = ["Circuits", "Candidates", "Results so far"] as const;

const NAMES = ["Amara Okoye", "Ben Hart", "Chloe Imran"];

let boards: BoardServer;
let org: SittingsOrg;
let sittingId: string;

test.beforeAll(async () => {
  test.setTimeout(600_000);
  boards = await serveBoards();
  org = await seedSittingsOrg({ adminName: "Ms Clarke", trainees: 3, supervisors: ["Dr Patel"], names: NAMES });
  const today = new Date();
  today.setHours(9, 0, 0, 0);
  sittingId = await seedSitting(org, {
    name: "March mock", mode: "exam", exam: "finals", scheduledFor: today, cohort: "Year 5",
    circuits: Array.from({ length: 3 }, (_, i) => ({
      name: `Circuit ${i + 1} · ${NAMES[i]}`, people: [i], supervisor: i === 2 ? "Ms Clarke" : "Dr Patel", stations: 6,
    })),
  });
});
test.afterAll(async () => boards?.close());

async function pages(browser: Browser, viewport: { width: number; height: number }): Promise<{ board: Page; app: Page }> {
  const boardContext = await browser.newContext({ viewport });
  const appContext = await browser.newContext({ viewport });
  await signedInAs(appContext, org.account);
  const board = await boardContext.newPage();
  const app = await appContext.newPage();
  await openBoard(board, boards, "Sitting");
  await board.addStyleTag({ content: ".tab:nth-child(n+4),.note,details.fold{display:none!important}" });
  await openPage(app, `/app/${org.slug}/sittings/${sittingId}`);
  await app.getByRole("tab", { name: "Circuits", exact: true }).waitFor();
  // The journeys (build-sitting) read the rail as a list named "Steps": the board has no such name, so pixels alone never see it go.
  await expect(app.getByRole("list", { name: "Steps" }).getByRole("listitem")).toHaveCount(6);
  await expect(app.getByRole("list", { name: "Steps" })).toContainText("Circuits");
  await app.evaluate(() => document.fonts.ready);
  return { board, app };
}

for (const viewport of VIEWPORTS) {
  for (const [index, label] of TABS.entries()) {
    test(`Sitting ${label} matches the board, ${viewport.name}`, async ({ browser }) => {
      const { board, app } = await pages(browser, viewport);
      await board.locator(".tab").nth(index).click();
      await app.getByRole("tab", { name: label, exact: true }).click();
      await board.mouse.move(0, 0);
      await app.mouse.move(0, 0);
      const tab = `tab-${index + 1}-${label.toLowerCase().replace(/ /g, "-")}-${viewport.name}`;
      const score = await compareRegion({ browser, boardPage: board, appPage: app, board: "Sitting", tab, viewport: viewport.name, boardRegion: ".page", appRegion: PAGE });
      console.log(`Sitting ${tab}: ${score.percent}% largest ${JSON.stringify(score.largest)} | ${score.files.side}`);
      expect(score.pass, `${tab}: ${score.percent}% differs, see ${score.files.side}`).toBe(true);
    });
  }
}
