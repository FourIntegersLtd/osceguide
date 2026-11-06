import { expect, test, type Page } from "@playwright/test";
import { MAX_DIFF_PERCENT, compareRegion, openBoard, serveBoards, type BoardServer } from "../support/board-diff";
import { examsOrg, type ExamsOrg } from "../support/seed-exams";
import { openPage, signedInAs } from "../support/session";

/**
 * CreateStation (docs/institution-overhaul/boards/CreateStation.dc.html), its four tabs, against the app at 1440 and 760.
 * Run: E2E_REUSE_SERVER=1 VERIFY_WEB_URL=http://localhost:3141 npx playwright test e2e/assess/board-create-station.spec.ts
 * Region: board `.page` against the app's [data-testid=create-station-page]. Board-only design notes are hidden.
 *
 * EXCEPTIONS:
 *  - Tabs 1 and 2 were 7.9 / 9.3 (desktop) before StationInstanceContentPanel and B2CPageHeader were changed for other boards
 *    (folds stacked flush, header offset); they now score 10.7 / 9.9 desktop and 12.5 / 11.9 mobile. Re-check after those settle.
 *  - Tabs 1 and 2 are held to the bar; the seeded "Communication station (v2)" has the board's four numbered text areas (seed-exams.ts).
 *  - Tab 3 ("No template (by exam)") and tab 4 ("Before a template is chosen") are state demos: the board stacks several states
 *    that never show together (a template-less exam with its layout, an info alert, "needs a template" and the generated draft
 *    over one another). The app shows one state at a time, so the score is logged and the app's own state is asserted instead.
 *  - The back link reads "Stations" (the page it returns to; journeys read it), the board's reads "New station".
 *  - The "An exam of your own has no built-in layout" sentence shows only while no template is chosen.
 *  - Phone: foundation sheets and drawer are kept (user decision).
 */
const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1100 },
  { name: "mobile", width: 760, height: 1100 },
] as const;
const TABS = ["Manual", "Generate with AI", "No template", "Before a template"] as const;

let boards: BoardServer;
let org: ExamsOrg;
test.beforeAll(async () => {
  test.setTimeout(600_000);
  boards = await serveBoards();
  org = await examsOrg();
});
test.afterAll(async () => boards?.close());

async function chooseTemplate(app: Page): Promise<void> {
  const select = app.getByLabel("Template", { exact: true });
  await select.waitFor();
  await expect(select.locator("option")).toHaveCount(await select.locator("option").count());
  await select.selectOption({ label: (await select.locator("option").allTextContents()).find((t) => t.includes("Communication station (v2)")) ?? "" });
}

for (const viewport of VIEWPORTS) {
  for (const [index, name] of TABS.entries()) {
    test(`CreateStation ${name} matches the board, ${viewport.name}`, async ({ browser }) => {
      test.setTimeout(180_000);
      const boardContext = await browser.newContext({ viewport });
      const appContext = await browser.newContext({ viewport });
      await signedInAs(appContext, org.account);
      const board = await boardContext.newPage();
      const app = await appContext.newPage();
      await openBoard(board, boards, "CreateStation");
      await board.locator(".tab").nth(index).click();
      await board.evaluate(() => { for (const el of Array.from(document.querySelectorAll<HTMLElement>(".note, details"))) if (el.classList.contains("note") || (el.querySelector("summary")?.textContent ?? "").startsWith("Build spec")) el.style.display = "none"; });
      const base = `/app/${org.slug}/authoring/stations/new`;
      if (index === 0) {
        await openPage(app, `${base}?start=layout&exam=finals`);
        await chooseTemplate(app);
      } else if (index === 1) {
        await openPage(app, `${base}?start=ai&exam=finals`);
        await chooseTemplate(app);
        await app.getByRole("tab", { name: "Generate with AI" }).click();
        // The board's tab shows a filled prompt, which also enables Generate draft.
        await app.getByPlaceholder(/^e\.g\. 72F falls/).fill("e.g. 72F falls at home, hip pain, shortened externally rotated leg. Candidate to assess and plan management including peri-op considerations.");
      } else if (index === 2) {
        await openPage(app, `${base}?start=blank&exam=finals`);
        await app.getByLabel("Station title").waitFor();
      } else {
        await openPage(app, `${base}?start=blank`);
        await app.getByLabel("Station title").waitFor();
      }
      await board.mouse.move(0, 0);
      await app.mouse.move(0, 0);
      const score = await compareRegion({ browser, boardPage: board, appPage: app, board: "CreateStation", tab: `${index + 1}-${viewport.name}`, viewport: viewport.name, boardRegion: ".page", appRegion: '[data-testid="create-station-page"]' });
      console.log(`CreateStation ${name} ${viewport.name}: ${score.percent}% | ${score.files.side}`);
      if (index < 2) expect.soft(score.percent < MAX_DIFF_PERCENT, `CreateStation ${name} ${viewport.name}: ${score.percent}%`).toBe(true);
      else await expect(app.getByRole("heading", { name: index === 2 ? "This exam needs a template" : "Choose a template or an exam" })).toBeVisible();
    });
  }
}
