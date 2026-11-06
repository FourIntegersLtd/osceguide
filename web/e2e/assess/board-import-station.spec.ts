import { expect, test, type Page } from "@playwright/test";
import { MAX_DIFF_PERCENT, compareRegion, openBoard, serveBoards, type BoardServer } from "../support/board-diff";
import { importStationOrg } from "../support/seed-import-station";
import type { ExamsOrg } from "../support/seed-exams";
import { openPage, signedInAs } from "../support/session";

/**
 * ImportStation (docs/institution-overhaul/boards/ImportStation.dc.html) against the app's dialog, at 1440 and 760.
 * Run: E2E_REUSE_SERVER=1 VERIFY_WEB_URL=http://localhost:3241 npx playwright test e2e/assess/board-import-station.spec.ts
 * Region: the board's `.page` (width pinned to the dialog's 568px, chrome hidden) against the app's [role=dialog].
 *
 * EXCEPTIONS:
 *  - The board draws the dialog full size as a page (card, 28px h1 above it); the app is a dialog with its title and lead inside the panel.
 *  - The board's head (28px h1, lead) sits outside its card, so the board is framed as a 520px panel with 24px padding and
 *    no card border, and the app's dialog title and lead are hidden. Tab 2 omits the Exam field and the recent list on the
 *    board; the app needs the exam and keeps the list, so both are hidden there. Tab 1's template is the org's first published layout, a seeded one (the dev database has no platform standard template to default to).
 *  - The board's footer buttons sit left under the card; a dialog's sit right (the board's own `.dlg .acts`).
 *  - The board's template_ready row also shows a "check these" note; the app writes review notes only once the station is drafted.
 *  - Tab 3 (Refusals) lists six alerts at once; the app shows one at a time, so it is asserted by words, not scored.
 *  - Phone: the dialog is a foundation bottom sheet (user decision).
 */
const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1100 },
  { name: "mobile", width: 760, height: 1100 },
] as const;

let boards: BoardServer;
let org: ExamsOrg;
test.beforeAll(async () => {
  test.setTimeout(600_000);
  boards = await serveBoards();
  org = await importStationOrg();
});
test.afterAll(async () => boards?.close());

const FILES = [
  { name: "bad-news.docx", mimeType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document", buffer: Buffer.from("x") },
  { name: "abdo-exam.pdf", mimeType: "application/pdf", buffer: Buffer.from("x") },
];

async function openDialog(app: Page): Promise<void> {
  await openPage(app, `/app/${org.slug}/authoring/stations`);
  await app.getByRole("button", { name: "Import from PDF or Word" }).click();
  await app.getByRole("dialog", { name: "Import from PDF or Word" }).waitFor();
  await app.getByLabel("Exam", { exact: true }).selectOption("finals");
}

for (const viewport of VIEWPORTS) {
  for (const index of [0, 1]) {
    test(`ImportStation tab ${index + 1} matches the board, ${viewport.name}`, async ({ browser }) => {
      test.setTimeout(180_000);
      const boardContext = await browser.newContext({ viewport });
      const appContext = await browser.newContext({ viewport });
      await signedInAs(appContext, org.account);
      const board = await boardContext.newPage();
      const app = await appContext.newPage();
      await openBoard(board, boards, "ImportStation");
      await board.locator(".tab").nth(index).click();
      await board.addStyleTag({ content: ".page{max-width:520px!important;padding:24px!important;background:#fff!important;border-radius:14px!important;gap:15px!important}.page>div:first-child,.head,.tabs,.note,details{display:none!important}.card.pad{border:0!important;padding:0!important;border-radius:0!important}" });
      if (viewport.width < 768) await board.addStyleTag({ content: ".page{max-width:none!important;width:752px!important;box-sizing:border-box!important}" });
      await openDialog(app);
      const templates = app.getByLabel("Template", { exact: true });
      if (index === 0) {
        await expect(templates.locator("option")).not.toHaveCount(1);
        const labels = await templates.locator("option").allTextContents();
        await templates.selectOption({ label: labels.find((t) => !t.startsWith("Make a new")) ?? "" });
        await app.locator('input[type="file"]').setInputFiles(FILES);
        await app.getByText("bad-news.docx, abdo-exam.pdf").waitFor();
      } else {
        await templates.selectOption({ label: "Make a new template from this file" });
        await app.addStyleTag({ content: '[role="dialog"] div:has(> label[for="import-exam"]),[role="dialog"] section[aria-label="Recent imports"]{display:none!important}' });
      }
      await app.addStyleTag({ content: '[role="dialog"] .flex-col > h2,[role="dialog"] .flex-col > h2 + div{display:none!important}' });
      await app.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
      await board.mouse.move(0, 0);
      await app.mouse.move(0, 0);
      const score = await compareRegion({ browser, boardPage: board, appPage: app, board: "ImportStation", tab: `${index + 1}-${viewport.name}`, viewport: viewport.name, boardRegion: ".page", appRegion: '[role="dialog"]' });
      console.log(`ImportStation tab ${index + 1} ${viewport.name}: ${score.percent}% | ${score.files.side}`);
      expect.soft(score.percent < MAX_DIFF_PERCENT, `ImportStation tab ${index + 1} ${viewport.name}: ${score.percent}%`).toBe(true);
    });
  }
}

test("ImportStation refusals are said in the board's words", async ({ browser }) => {
  const context = await browser.newContext({ viewport: VIEWPORTS[0] });
  await signedInAs(context, org.account);
  const app = await context.newPage();
  await openDialog(app);
  await app.getByRole("dialog").getByText("Recent imports").waitFor();
  for (const name of ["chest-pain.pdf", "bad-news.docx", "abdo-exam.pdf", "scan.pdf"]) await expect(app.getByRole("dialog").getByText(name)).toBeVisible();
  await expect(app.getByRole("button", { name: "Publish template and create the station" })).toBeVisible();
  await expect(app.getByRole("link", { name: "Review the template" })).toBeVisible();
  await app.locator('input[type="file"]').setInputFiles({ name: "notes.txt", mimeType: "text/plain", buffer: Buffer.from("x") });
  await expect(app.getByText("Only PDF and Word (.docx) files can be imported.")).toBeVisible();
});
