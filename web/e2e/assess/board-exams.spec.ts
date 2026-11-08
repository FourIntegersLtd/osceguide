import { expect, test, type Browser, type Page } from "@playwright/test";
import { MAX_DIFF_PERCENT, compareRegion, openBoard, serveBoards, type BoardServer } from "../support/board-diff";
import { examsOrg, type ExamsOrg } from "../support/seed-exams";
import { openPage, signedInAs } from "../support/session";

/**
 * Exams (docs/institution-overhaul/boards/Exams.dc.html) against the app, tab by tab, at 1440 and 760.
 * Run: E2E_REUSE_SERVER=1 npx playwright test -c playwright.exams.config.ts e2e/assess/board-exams.spec.ts
 * PNGs and scores.json land in docs/institution-overhaul/verify/board-diff/.
 *
 * Compared region: the page content (the board's `.page`, the app's `max-w-osce-page` column); the
 * sidebar is the app shell, owned by its own board.
 *
 * Board-only text that is design commentary, not product UI, is hidden on the board side before the
 * screenshot (ANNOTATIONS): the grey explanatory lines under each list and the "What changed" note.
 * No other mask is used; the Created at column is a named exception (EXCEPTIONS below).
 *
 * EXCEPTIONS (a board state the api cannot reach, or a control the board does not draw but the
 * product keeps), each written where it applies:
 *  - Stations: the board's "14 stations" header and "Load more" row describe a longer list than the
 *    three sample rows; the app counts what it shows. "Used by 3" needs three circuits on the station.
 *    "Created at" is the time the seed ran, not 12/10/2026.
 *  - Edit exam dialog: the board draws a sketch with no fields; the app keeps the working form (shell, heading and
 *    footer match; the fields are the difference).
 *  - Tabs 1-5 at 1440 sit at 10-14%: the user's spacing rhythm (DESIGN.md "Spacing rhythm and quiet selection",
 *    24px row padding against the board's 20px) adds a few px per row, so the drift compounds down a list. Programmes
 *    also lacks the Draft and Retired rows (a draft exam cannot take a programme).
 *  - Add programme: the board draws "Add programme" enabled; the app disables it until an exam is chosen.
 *  - Phone dialogs (760): the foundation bottom sheet is kept; a user decision is pending.
 *  - New exam / New station chooser: the 1px light selection border and the 16px option rhythm (same DESIGN.md block).
 */
const APP_PAGE = '[data-testid="exams-page"]';
/** The acceptance bar: board-diff.ts MAX_DIFF_PERCENT. */
const MAX_PERCENT = MAX_DIFF_PERCENT;
const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1100 },
  { name: "mobile", width: 760, height: 1100 },
] as const;

/** Design commentary on the board, not product UI. */
const ANNOTATIONS = [
  'The "Ready to schedule"',
  '"Approved" / "Awaiting approval"',
  "An OSCE Guide template offers only",
  'In the redesign the exam',
  "What changed:",
];

let boards: BoardServer;
let org: ExamsOrg;

test.beforeAll(async () => {
  test.setTimeout(900_000);
  boards = await serveBoards();
  org = await examsOrg();
});
test.afterAll(async () => boards?.close());

/** Hide the board's design commentary; run after a tab click, which redraws the board's content. */
async function hideAnnotations(board: Page): Promise<void> {
  await board.evaluate((notes) => {
    for (const el of Array.from(document.querySelectorAll<HTMLElement>(".meta, .note"))) {
      if (notes.some((n) => (el.textContent ?? "").trim().startsWith(n)) && !el.closest(".fold")) el.style.display = "none";
    }
    for (const fold of Array.from(document.querySelectorAll<HTMLElement>("details.fold"))) fold.style.display = "none";
  }, ANNOTATIONS);
}

/**
 * NAMED EXCEPTION, platform rows: the local api also lists OSCE Guide's own exams, marking schemes and
 * station layouts (CASC, Ortho, PLAB 2 ...), which the board's three-row sample omits and the seed cannot
 * remove. Rows whose title is not a board row title (or its alias) are hidden on the app side before the
 * shot. The raw, unfiltered score is printed beside it ("raw") so nothing is hidden silently.
 */
const ROW_ALIASES: Record<string, string> = { SCA: "Simulated Consultation Assessment", "SCA domains": "Simulated Consultation Assessment marking rubric" };
async function hidePlatformRows(board: Page, app: Page): Promise<void> {
  const titles = await board.evaluate(() =>
    Array.from(document.querySelectorAll<HTMLElement>(".page .row")).map((r) => (r.innerText ?? "").trim().split("\n")[0] ?? ""),
  );
  const bare = (t: string) => t.replace(/^🎓\s*/u, "");
  const keep = titles.flatMap((t) => [bare(t), bare(ROW_ALIASES[bare(t)] ?? t)]).filter(Boolean);
  await app.evaluate((names) => {
    for (const row of Array.from(document.querySelectorAll<HTMLElement>("[data-row]"))) {
      const title = ((row.innerText ?? "").trim().split("\n")[0] ?? "").replace(/^🎓\s*/u, "");
      if (!names.includes(title)) row.style.display = "none";
    }
  }, keep);
}

async function pages(browser: Browser, viewport: { width: number; height: number }): Promise<{ board: Page; app: Page }> {
  const boardContext = await browser.newContext({ viewport });
  const appContext = await browser.newContext({ viewport });
  await signedInAs(appContext, org.account);
  const board = await boardContext.newPage();
  const app = await appContext.newPage();
  await openBoard(board, boards, "Exams");
  return { board, app };
}

const TABS = [
  { name: "exams", index: 0, ready: "Final MB OSCE" },
  { name: "stations", index: 1, ready: "Breaking bad news" },
  { name: "marking-schemes", index: 2, ready: "Consultation skills" },
  { name: "station-layouts", index: 3, ready: "Communication station" },
  { name: "programmes", index: 4, ready: "🎓 Final MB OSCE" },
  { name: "empty-states", index: 5, ready: "No exams yet" },
] as const;
const ROUTES = ["exams", "stations", "rubrics", "station-templates", "programmes", "states"];

for (const viewport of VIEWPORTS) {
  for (const tab of TABS) {
    test(`Exams tab ${tab.index + 1} ${tab.name} matches the board, ${viewport.name}`, async ({ browser }) => {
      const { board, app } = await pages(browser, viewport);
      await board.locator(".tab").nth(tab.index).click();
      await hideAnnotations(board);
      await openPage(app, `/app/${org.slug}/authoring/${ROUTES[tab.index]}`);
      await app.getByText(tab.ready, { exact: true }).first().waitFor();
      await board.mouse.move(0, 0);
      await app.mouse.move(0, 0);
      const region = { browser, boardPage: board, appPage: app, board: "Exams", viewport: viewport.name, boardRegion: ".page", appRegion: APP_PAGE };
      const raw = await compareRegion({ ...region, tab: `${tab.index + 1}-${tab.name}-${viewport.name}-raw` });
      console.log(`Exams ${tab.name} ${viewport.name} raw (platform rows shown): ${raw.percent}% | ${raw.files.side}`);
      await hidePlatformRows(board, app);
      const score = await compareRegion({ ...region, tab: `${tab.index + 1}-${tab.name}-${viewport.name}` });
      console.log(`Exams ${tab.name} ${viewport.name}: ${score.percent}% largest ${JSON.stringify(score.largest)} | ${score.files.side}`);
      expect.soft(score.percent < MAX_PERCENT, `${tab.name} ${viewport.name}: ${score.percent}% differs, largest ${JSON.stringify(score.largest)}, see ${score.files.side}`).toBe(true);
    });
  }
}

// New exam (docs/institution-overhaul/boards/NewExam.dc.html): the sheet's steps 1-4, board `.wrap` against the app's body.
// EXCEPTIONS: step 2's "Use one of your marking schemes" lists the org's real schemes; step 3 draws the
// timing fields as numbers with a "min" hint where the board shows "3 min"; the product's "Attempts per station"
// control (the board lacks it) stays.
/* The app generates the code; earlier runs are found by the name this spec types. */
const NEW_EXAM_NAME = "Paediatrics block";
async function dropNewExam(): Promise<void> {
  const { call, orgPath } = await import("../support/api");
  const list = await call<{ items: { id: string; name: string }[] }>(org.token, orgPath(org.slug, `/exams?status=all`));
  for (const e of list.items.filter((x) => x.name === NEW_EXAM_NAME)) await call(org.token, orgPath(org.slug, `/exams/${e.id}`), { method: "DELETE" });
}

for (const viewport of VIEWPORTS) {
  test(`New exam steps 1-4 match the board, ${viewport.name}`, async ({ browser }) => {
    test.setTimeout(240_000);
    const boardContext = await browser.newContext({ viewport });
    const appContext = await browser.newContext({ viewport });
    await signedInAs(appContext, org.account);
    const board = await boardContext.newPage();
    const app = await appContext.newPage();
    await dropNewExam();
    try {
      await board.goto(boards.url("NewExam"));
      await board.waitForSelector("body[data-dc-ready='1']");
      await board.evaluate(() => document.fonts.ready);
      await openPage(app, `/app/${org.slug}/authoring/exams/new`);
      const names = ["1-name", "2-marking-scheme", "3-timings", "4-publish"];
      for (let step = 0; step < 4; step++) {
        if (step === 0) {
          await app.getByLabel("Exam name").fill(NEW_EXAM_NAME);
        }
        await board.locator(".st").nth(step).click();
        await board.evaluate(() => { document.querySelectorAll<HTMLElement>("details.fold, .fold").forEach((el) => { el.style.display = "none"; }); });
        await app.getByText(`Step ${step + 1} of 4`).waitFor();
        await board.mouse.move(0, 0);
        if (step === 1) await app.getByRole("radio").nth(1).click(); // the board has "Copy one from OSCE Guide" selected
        await app.mouse.move(0, 0);
        const score = await compareRegion({ browser, boardPage: board, appPage: app, board: "NewExam", tab: `${names[step]}-${viewport.name}`, viewport: viewport.name, boardRegion: ".wrap", appRegion: '[data-testid="new-exam-body"]' });
        console.log(`NewExam ${names[step]} ${viewport.name}: ${score.percent}% largest ${JSON.stringify(score.largest)} | ${score.files.side}`);
        expect.soft(score.percent < MAX_PERCENT, `new exam ${names[step]} ${viewport.name}: ${score.percent}%, see ${score.files.side}`).toBe(true);
        if (step === 1) {
          await app.getByRole("radio").nth(0).click(); // back to "Use": it holds the version picker Continue needs
          await app.getByRole("combobox").first().selectOption({ index: 1 });
        }
        if (step < 3) await app.getByRole("button", { name: "Continue" }).click();
      }
    } finally {
      await dropNewExam();
    }
  });
}

// Dialogs: board `.dlg` against the app's open dialog, opened from the same row button.
// EXCEPTIONS: Archive station's title carries "(v2)" and "Used 3 times" (a station used by three circuits cannot
// be seeded); Edit exam: the board sketches a box with no fields, the app keeps its working form; Delete template
// uses a FINALS template (the api refuses a template on the draft Y4-MOCK exam).
const DIALOGS = [
  { name: "retire", tab: 0, row: "Final MB OSCE", button: "Retire" },
  { name: "delete-exam", tab: 0, row: "Year 4 mock", button: "Delete" },
  { name: "edit-exam", tab: 0, row: "Final MB OSCE", button: "Edit" },
  { name: "archive-station", tab: 1, row: "Breaking bad news", button: "Archive" },
  { name: "archive-live", tab: 3, row: "Communication station", button: "Archive live" },
  { name: "delete-draft", tab: 3, row: "Communication station", button: "Delete draft" },
  { name: "delete-template", tab: 3, row: "Untitled template", button: "Delete draft" },
  { name: "add-programme", tab: 4, row: "", button: "New programme" },
] as const;

const IN_MENU = new Set<string>(["Retire", "Delete", "Archive", "Archive live", "Delete draft"]);

for (const viewport of VIEWPORTS) {
  for (const dialog of DIALOGS) {
    test(`Dialog ${dialog.name} matches the board, ${viewport.name}`, async ({ browser }) => {
      const { board, app } = await pages(browser, viewport);
      await board.locator(".tab").nth(dialog.tab).click();
      await openPage(app, `/app/${org.slug}/authoring/${ROUTES[dialog.tab]}`);
      await app.getByText(TABS[dialog.tab]!.ready, { exact: true }).first().waitFor();
      const boardRow = dialog.row ? board.locator(".row").filter({ hasText: dialog.row }).first() : board.locator(".page");
      await boardRow.getByRole("button", { name: dialog.button, exact: true }).first().click();
      const appScope = dialog.row ? app.locator("[data-row]").filter({ hasText: dialog.row }).first() : app.locator(APP_PAGE);
      if (IN_MENU.has(dialog.button)) {
        // The app keeps one inline action per row and puts the rest in its "⋯" menu; the board still draws buttons.
        // The row can re-render as its data settles and close a menu opened too early: open it again until the item shows.
        const item = app.getByRole("menuitem", { name: dialog.button, exact: true });
        await expect(async () => {
          if (!(await item.isVisible())) {
            const trigger = appScope.getByRole("button", { name: /^Actions for / }).first();
            await trigger.scrollIntoViewIfNeeded();
            await trigger.click();
          }
          await expect(item).toBeVisible({ timeout: 2000 });
        }).toPass({ timeout: 20_000 });
        // A fixed menu closes on scroll and a click can scroll: press the focused item instead.
        await item.focus();
        await app.keyboard.press("Enter");
      } else {
        await appScope.getByRole("button", { name: dialog.button, exact: true }).first().click();
      }
      await app.getByRole("dialog").waitFor();
      await board.mouse.move(0, 0);
      await app.mouse.move(0, 0);
      const score = await compareRegion({ browser, boardPage: board, appPage: app, board: "Exams", tab: `dialog-${dialog.name}-${viewport.name}`, viewport: viewport.name, boardRegion: ".dlg", appRegion: '[role="dialog"]' });
      console.log(`Dialog ${dialog.name} ${viewport.name}: ${score.percent}% | ${score.files.side}`);
      expect.soft(score.percent < MAX_PERCENT, `dialog ${dialog.name} ${viewport.name}: ${score.percent}%, see ${score.files.side}`).toBe(true);
    });
  }
}

// New station chooser (docs/institution-overhaul/boards/NewStation.dc.html): the board's `.sheet` against the app's sheet,
// once per way of starting. EXCEPTION: the "For exam" list shows this org's real exams, so the chosen name differs.
const WAYS = ["layout", "import", "ai", "library", "blank"];
for (const viewport of VIEWPORTS) {
  test(`New station chooser matches the board, ${viewport.name}`, async ({ browser }) => {
    test.setTimeout(240_000);
    const boardContext = await browser.newContext({ viewport });
    const appContext = await browser.newContext({ viewport });
    await signedInAs(appContext, org.account);
    const board = await boardContext.newPage();
    const app = await appContext.newPage();
    await board.goto(boards.url("NewStation"));
    await board.waitForSelector("body[data-dc-ready='1']");
    await board.evaluate(() => document.fonts.ready);
    await board.evaluate(() => { document.querySelectorAll<HTMLElement>("details.fold").forEach((el) => { el.style.display = "none"; }); });
    await openPage(app, `/app/${org.slug}/authoring/stations/new`);
    await app.getByLabel("For exam").selectOption({ index: 1 });
    for (const [index, way] of WAYS.entries()) {
      await board.locator(".way").nth(index).click();
      await app.getByRole("radio").nth(index).click();
      await board.mouse.move(0, 0);
      await app.mouse.move(0, 0);
      const score = await compareRegion({ browser, boardPage: board, appPage: app, board: "NewStation", tab: `${way}-${viewport.name}`, viewport: viewport.name, boardRegion: ".sheet", appRegion: '[data-testid="new-station-sheet"] > div' });
      console.log(`NewStation ${way} ${viewport.name}: ${score.percent}% largest ${JSON.stringify(score.largest)} | ${score.files.side}`);
      expect.soft(score.percent < MAX_PERCENT, `new station ${way} ${viewport.name}: ${score.percent}%, see ${score.files.side}`).toBe(true);
    }
  });
}
