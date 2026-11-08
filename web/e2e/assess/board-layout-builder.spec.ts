import { expect, test } from "@playwright/test";
import { MAX_DIFF_PERCENT, compareRegion, openBoard, serveBoards, type BoardServer } from "../support/board-diff";
import { layoutBuilderWorld, type LayoutBuilderWorld } from "../support/seed-layout-builder";
import { openPage, signedInAs } from "../support/session";

/**
 * LayoutBuilder (docs/institution-overhaul/boards/LayoutBuilder.dc.html), tabs 1-4, against the app at 1440 and 760.
 * Run: E2E_REUSE_SERVER=1 VERIFY_WEB_URL=http://localhost:3197 npx playwright test e2e/assess/board-layout-builder.spec.ts
 * Region: board `.page` against the app's [data-testid=layout-builder-page]. Board-only notes, tab bar and the Build spec fold are hidden.
 *
 * EXCEPTIONS:
 *  - Tab 5 (loading, error, not found, empty states) is a list of separate states on the board, not one screen: the
 *    not-found words are asserted below, the rest are listed in the report and not scored.
 *  - Phone: foundation sheets and drawer are kept (user decision).
 */
const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 2000 },
  { name: "mobile", width: 760, height: 2000 },
] as const;
const TABS = ["New: start", "New: sections and fields", "Edit draft", "View a published version"] as const;

let boards: BoardServer;
let world: LayoutBuilderWorld;
test.beforeAll(async () => {
  test.setTimeout(600_000);
  boards = await serveBoards();
  world = await layoutBuilderWorld();
});
test.afterAll(async () => boards?.close());

for (const viewport of VIEWPORTS) {
  for (const [index, name] of TABS.entries()) {
    test(`LayoutBuilder ${name} matches the board, ${viewport.name}`, async ({ browser }) => {
      test.setTimeout(180_000);
      const boardContext = await browser.newContext({ viewport });
      const appContext = await browser.newContext({ viewport });
      await signedInAs(appContext, world.org.account);
      const board = await boardContext.newPage();
      const app = await appContext.newPage();
      await openBoard(board, boards, "LayoutBuilder");
      await board.locator(".tab").nth(index).click();
      await board.evaluate(() => { for (const el of Array.from(document.querySelectorAll<HTMLElement>(".note, details.fold, details, .tabs"))) { if (el.matches(".note, .tabs") || (el.querySelector("summary")?.textContent ?? "").startsWith("Build spec")) el.style.display = "none"; } });
      const base = `/app/${world.org.slug}/authoring/station-templates`;
      if (index < 2) {
        await openPage(app, `${base}/new?exam=ortho`);
        await app.getByLabel("Template title").or(app.getByPlaceholder("Untitled template")).first().waitFor();
        await app.getByRole("radio", { name: /^Communication\./ }).check();
        if (index === 1) {
          await app.getByPlaceholder("Untitled template").fill("Communication station");
          await app.getByRole("button", { name: "Continue" }).click();
          await app.getByText("Step 2 of 2: sections and fields.").waitFor();
        }
      } else {
        const id = index === 2 ? world.draftId : world.publishedId;
        await openPage(app, `${base}/${id}/versions/${index === 2 ? 3 : 2}`);
        await app.getByText(/^Version \d/).waitFor();
      }
      await board.mouse.move(0, 0);
      await app.mouse.move(0, 0);
      const score = await compareRegion({ browser, boardPage: board, appPage: app, board: "LayoutBuilder", tab: `${index + 1}-${viewport.name}`, viewport: viewport.name, boardRegion: ".page", appRegion: '[data-testid="layout-builder-page"]' });
      console.log(`LayoutBuilder ${name} ${viewport.name}: ${score.percent}% | ${score.files.side}`);
      expect.soft(score.percent < MAX_DIFF_PERCENT, `LayoutBuilder ${name} ${viewport.name}: ${score.percent}%`).toBe(true);
    });
  }
}

test("LayoutBuilder not found state keeps the board's words", async ({ browser }) => {
  const context = await browser.newContext({ viewport: VIEWPORTS[0] });
  await signedInAs(context, world.org.account);
  const app = await context.newPage();
  await openPage(app, `/app/${world.org.slug}/authoring/station-templates/${world.draftId}/versions/99`);
  await expect(app.getByText("Template not found. It may have been removed.")).toBeVisible();
});

test("LayoutBuilder title is edited on the section, settings open in a dialog without it, and Preview groups sections by audience", async ({ browser }) => {
  const context = await browser.newContext({ viewport: VIEWPORTS[0] });
  await signedInAs(context, world.org.account);
  const app = await context.newPage();
  await openPage(app, `/app/${world.org.slug}/authoring/station-templates/${world.draftId}/versions/3`);
  await app.getByRole("tab", { name: "Build" }).waitFor();

  await app.getByLabel("Section title").fill("Opening brief");
  await app.getByRole("button", { name: "Section settings" }).click();
  const dialog = app.getByRole("dialog", { name: "Section settings" });
  await expect(dialog.getByRole("radiogroup", { name: "Written for" })).toBeVisible();
  await expect(dialog.getByLabel("Title")).toHaveCount(0);
  await expect(dialog.getByLabel("Description")).toHaveCount(0);
  await dialog.getByRole("button", { name: "Done" }).click();
  await expect(dialog).toBeHidden();

  await app.getByRole("tab", { name: "Preview" }).click();
  const candidate = app.getByRole("region", { name: "Candidate" });
  await expect(candidate.getByRole("heading", { name: "Candidate" })).toBeVisible();
  await expect(candidate.getByText("Opening brief").first()).toBeVisible();
  await expect(app.getByRole("region", { name: "Patient" }).getByText("Patient script").first()).toBeVisible();
});

test("LayoutBuilder published version is read only on Build, while Preview and section navigation still work", async ({ browser }) => {
  const context = await browser.newContext({ viewport: VIEWPORTS[0] });
  await signedInAs(context, world.org.account);
  const app = await context.newPage();
  await openPage(app, `/app/${world.org.slug}/authoring/station-templates/${world.publishedId}/versions/2`);
  await app.getByRole("tab", { name: "Build" }).waitFor();

  await expect(app.getByRole("tab", { name: "Preview" })).toBeEnabled();
  await expect(app.getByLabel("Section title")).toBeDisabled();
  await expect(app.getByRole("button", { name: "Add section" })).toBeDisabled();
  const second = app.getByRole("complementary", { name: "Sections" }).getByRole("tab").nth(1);
  await second.click();
  await expect(second).toHaveAttribute("aria-selected", "true");
  // Undo is frozen with the fields: the key does nothing on a published version.
  await app.keyboard.press("Control+z");
  await expect(app.getByLabel("Section title")).toBeDisabled();
  await app.getByRole("button", { name: "Next section" }).click();
  await expect(app.getByRole("complementary", { name: "Sections" }).getByRole("tab").nth(2)).toHaveAttribute("aria-selected", "true");

  await app.getByRole("tab", { name: "Preview" }).click();
  await expect(app.getByRole("region", { name: "Candidate" })).toBeVisible();
  await expect(app.getByRole("region", { name: "Patient" })).toBeVisible();
});
