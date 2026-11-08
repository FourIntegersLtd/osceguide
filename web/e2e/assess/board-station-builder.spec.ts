import { expect, test } from "@playwright/test";
import { MAX_DIFF_PERCENT, compareRegion, openBoard, serveBoards, type BoardServer } from "../support/board-diff";
import { stationBuilderWorld, type StationBuilderWorld } from "../support/seed-station-builder";
import { openPage, signedInAs } from "../support/session";

/**
 * StationBuilder (docs/institution-overhaul/boards/StationBuilder.dc.html), its four tabs, against the app at 1440 and 760.
 * Run: E2E_REUSE_SERVER=1 VERIFY_WEB_URL=http://localhost:3195 npx playwright test e2e/assess/board-station-builder.spec.ts
 * Region: board `.page` against the app's [data-testid=station-builder-page]. Board-only notes, the board's own tab bar and the Build spec fold are hidden.
 *
 * EXCEPTIONS:
 *  - The board's sample is v3 of three; the seeded stations read "version 2" (draft v3 on the draft one) because a station
 *    cannot be given a v3 without a longer publish and archive cycle; the history rows differ only in dates and "Used by" counts.
 *  - Tab 4 draws two error lines (no structure in the catalogue, no layout for the exam) under an archived station; the app
 *    shows at most one, and neither on a station that has a layout, so the archived tab is compared without them.
 *  - Dates read "6 Nov" (seed day) not "12 Oct"; "Used by 3" needs exams linked to the station (no cheap seed).
 *  - The board's title is an input on every tab; the app's is an h2 once the station is published or archived (not renamable).
 *  - Published and archived seeds have no v3 draft, so their history has fewer rows and the content is read only (no add-by-URL row).
 *  - An unsaved draft shows no rail; an archived station shows no brief card or content fold. Both are behaviour, not styling.
 *  - Phone: foundation sheets and drawer are kept (user decision).
 */
const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 2000 },
  { name: "mobile", width: 760, height: 2000 },
] as const;
const TABS = [
  { name: "Draft, ready", key: "draft" },
  { name: "Draft, unsaved", key: "draft" },
  { name: "Published", key: "published" },
  { name: "Archived", key: "archived" },
] as const;

let boards: BoardServer;
let world: StationBuilderWorld;
test.beforeAll(async () => {
  test.setTimeout(600_000);
  boards = await serveBoards();
  world = await stationBuilderWorld();
});
test.afterAll(async () => boards?.close());

for (const viewport of VIEWPORTS) {
  for (const [index, tab] of TABS.entries()) {
    test(`StationBuilder ${tab.name} matches the board, ${viewport.name}`, async ({ browser }) => {
      test.setTimeout(180_000);
      const boardContext = await browser.newContext({ viewport });
      const appContext = await browser.newContext({ viewport });
      await signedInAs(appContext, world.org.account);
      const board = await boardContext.newPage();
      const app = await appContext.newPage();
      await openBoard(board, boards, "StationBuilder");
      await board.locator(".tab").nth(index).click();
      await board.evaluate(() => { for (const el of Array.from(document.querySelectorAll<HTMLElement>(".note, details.fold, .tabs, .meta"))) { const text = el.textContent ?? ""; if (el.matches(".note, .tabs") || (el.matches("details.fold") && (el.querySelector("summary")?.textContent ?? "").startsWith("Build spec")) || (el.matches(".meta") && text.startsWith("Leaving now"))) el.style.display = "none"; } });
      await openPage(app, `/app/${world.org.slug}/authoring/stations?status=all&station=${world[tab.key]}`);
      await app.getByTestId("station-builder-page").waitFor();
      if (index === 1) {
        // Unsaved: the board's candidate brief is cleared, which leaves a required field empty.
        const brief = app.getByRole("textbox").nth(1);
        await brief.fill("x");
        await brief.fill("");
        await brief.blur();
      }
      await board.mouse.move(0, 0);
      await app.mouse.move(0, 0);
      const score = await compareRegion({ browser, boardPage: board, appPage: app, board: "StationBuilder", tab: `${index + 1}-${viewport.name}`, viewport: viewport.name, boardRegion: ".page", appRegion: '[data-testid="station-builder-page"]' });
      console.log(`StationBuilder ${tab.name} ${viewport.name}: ${score.percent}% | ${score.files.side}`);
      expect.soft(score.percent < MAX_DIFF_PERCENT, `StationBuilder ${tab.name} ${viewport.name}: ${score.percent}%`).toBe(true);
    });
  }
}

// The seeded stations hold no text in their candidate section, so the flat reading brief is still the candidate's.
test("an unsaved rename keeps the typed reading brief", async ({ browser }) => {
  test.setTimeout(120_000);
  const context = await browser.newContext({ viewport: VIEWPORTS[0] });
  await signedInAs(context, world.org.account);
  const app = await context.newPage();
  await openPage(app, `/app/${world.org.slug}/authoring/stations?status=all&station=${world.draft}`);
  await app.getByTestId("station-builder-page").waitFor();
  const brief = app.getByLabel("Reading brief");
  await brief.fill("Typed but not yet saved");
  const title = app.getByTestId("station-builder-page").getByRole("textbox").first();
  await title.fill("Breaking bad news, renamed");
  await expect(brief).toHaveCount(1);
  await expect(brief).toHaveValue("Typed but not yet saved");
  await title.fill("Breaking bad news");
  await expect(brief).toBeVisible();
  await expect(brief).toHaveValue("Typed but not yet saved");
  await context.close();
});

// Approval gates the platform library only: an organisation's own published station is never "Awaiting approval".
test("an org workspace lists its published station without an approval label", async ({ browser }) => {
  test.setTimeout(120_000);
  const context = await browser.newContext({ viewport: VIEWPORTS[0] });
  await signedInAs(context, world.org.account);
  const app = await context.newPage();
  await openPage(app, `/app/${world.org.slug}/authoring/stations?status=all`);
  await expect(app.getByText("Published").first()).toBeVisible();
  await expect(app.getByText("Awaiting approval")).toHaveCount(0);
  await expect(app.getByRole("button", { name: /^Approve$/ })).toHaveCount(0);
  await context.close();
});
