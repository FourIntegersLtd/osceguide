import { expect, test } from "@playwright/test";
import { MAX_DIFF_PERCENT, compareRegion, openBoard, serveBoards, type BoardServer } from "../support/board-diff";
import { call, orgPath } from "../support/api";
import { examsOrg, type ExamsOrg } from "../support/seed-exams";
import { openPage, signedInAs } from "../support/session";

/**
 * ExamSettings (docs/institution-overhaul/boards/ExamSettings.dc.html), tab 1 (edit an exam), against the app at 1440 and 760.
 * Run: E2E_REUSE_SERVER=1 VERIFY_WEB_URL=http://localhost:3187 npx playwright test e2e/assess/board-exam-settings.spec.ts
 *
 * Compared region: the page content (board `.page`, the app's page root). Board-only notes are hidden; the app's
 * "Exam settings" fold is opened to match the board.
 *
 * EXCEPTIONS:
 *  - Tabs 2 (create an exam) and 3 (states) are not compared: create is a sheet in the app (NewExamSheet), and the
 *    states tab stacks several states on one page.
 *  - The app adds a "Break between stations" field and shows the exam's name on the eyebrow.
 *  - Viewport height 2400: the app scrolls inside its shell, so an element screenshot of a long page is clipped.
 *  - Phone: foundation sheets and drawer are kept (user decision).
 */
const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 2400 },
  { name: "mobile", width: 760, height: 2400 },
] as const;

let boards: BoardServer;
let org: ExamsOrg;

test.beforeAll(async () => {
  test.setTimeout(900_000);
  boards = await serveBoards();
  org = await examsOrg();
});
test.afterAll(async () => boards?.close());

for (const viewport of VIEWPORTS) {
  test(`ExamSettings matches the board, ${viewport.name}`, async ({ browser }) => {
    test.setTimeout(180_000);
    const boardContext = await browser.newContext({ viewport });
    const appContext = await browser.newContext({ viewport });
    await signedInAs(appContext, org.account);
    const board = await boardContext.newPage();
    const app = await appContext.newPage();
    await openBoard(board, boards, "ExamSettings");
    await board.evaluate(() => {
      for (const el of Array.from(document.querySelectorAll<HTMLElement>(".note, details.fold"))) {
        if (el.classList.contains("note") || (el.querySelector("summary")?.textContent ?? "").startsWith("Build spec")) el.style.display = "none";
      }
    });
    // The board edits a draft exam ("Publish: Draft"): copy the seeded exam's scheme onto a fresh, unpublished one.
    const list = await call<{ items: { id: string; code: string; rubric_version_id: string | null }[] }>(org.token, orgPath(org.slug, "/exams"));
    const seeded = list.items.find((e) => e.code === "finals");
    if (!seeded) throw new Error("no exam seeded");
    const exam = await call<{ id: string }>(org.token, orgPath(org.slug, "/exams"), {
      method: "POST",
      body: { code: `mb-${viewport.name}-${Date.now() % 100000}`, name: "Final MB OSCE", default_reading_seconds: 120, default_simulation_seconds: 600, station_attempt_limit: 3, rubric_version_id: seeded.rubric_version_id },
    });
    await openPage(app, `/app/${org.slug}/authoring/exams/${exam.id}/settings`);
    await app.getByRole("heading", { name: "Exam settings" }).first().waitFor();
    await app.locator("summary", { hasText: "Exam settings" }).first().click();
    // Board-only: the tab strip that switches its states, and the app's extra "Break between stations" field.
    await board.evaluate(() => document.querySelector<HTMLElement>(".tabs")?.style.setProperty("display", "none"));
    await app.getByText("Break between stations").first().evaluate((el) => { (el.closest("label") ?? el).parentElement?.style.setProperty("display", "none"); });
    await board.mouse.move(0, 0);
    await app.mouse.move(0, 0);
    const score = await compareRegion({ browser, boardPage: board, appPage: app, board: "ExamSettings", tab: `1-${viewport.name}`, viewport: viewport.name, boardRegion: ".page", appRegion: '[data-testid="exam-settings-page"]' });
    console.log(`ExamSettings ${viewport.name}: ${score.percent}% largest ${JSON.stringify(score.largest)} | ${score.files.side}`);
    expect.soft(score.percent < MAX_DIFF_PERCENT, `ExamSettings ${viewport.name}: ${score.percent}%, see ${score.files.side}`).toBe(true);
  });
}
