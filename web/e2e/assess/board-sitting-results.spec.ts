import { expect, test, type Browser, type Page } from "@playwright/test";
import { compareRegion, openBoard, serveBoards, type BoardServer } from "../support/board-diff";
import { seedResultsOrg, type ResultsOrg } from "../support/seed-results";
import { openPage, signedInAs } from "../support/session";

/**
 * Sitting results (docs/institution-overhaul/boards/SittingResults.dc.html) against the app, for the seeded March
 * mock. Run: npx playwright test e2e/assess/board-sitting-results.spec.ts.
 *
 * The board's "Results" tab is one composite sample page, so it is compared block by block: heading, outcome
 * tiles, progress and release card, review order, candidates card and the opened decision (Ben Hart, a draft).
 * Named exceptions (none is a mask over app output beyond these):
 *  - The board draws two review-order rows, three candidate rows, three release rows and two stations of the
 *    app's eight, six and three; the other rows are removed and the rest put in the board's order on the app
 *    side (`keepRows`), so the blocks compare like for like.
 *  - Data the seed cannot match: the board's sample scores ("72/100") and reviews ("6 of 6 reviewed") need a
 *    marking engine and reviewer rows; its Ben Hart sample has no outcome yet an outcome chosen. The seeded draft
 *    has a fail, a rationale and no reviews, so those cells and the warning bar differ by data, not layout.
 *  - The decision's station titles are the local library's, renamed to the board's on the app side (board-rhythm
 *    test only); a station's "Green" chip and the "6 of 6 reviewed" tile need a marking engine and reviewer rows.
 *  - The release step's note reads "Not started" where the board prints "0 of 8 released" (sittingSteps.ts, not
 *    this slice's file).
 *  - `.note`, the build-spec fold and the board's own page-state tabs are annotations or switches, hidden.
 *  - Spacing rhythm (user rule, DESIGN.md "Spacing rhythm"): the decision form stacks its fields 28px apart with
 *    8px from label to control; the board uses 14px and 6px. This is the decision card's whole difference.
 *  - Selection and focus use the 1px light border tokens, not the board's saturated blue.
 */
const PAGE = 'section[aria-label="Results"]';
const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1700 },
  { name: "mobile", width: 760, height: 1700 },
] as const;

let boards: BoardServer;
let org: ResultsOrg;
test.beforeAll(async () => {
  test.setTimeout(600_000);
  boards = await serveBoards();
  org = await seedResultsOrg();
});
test.afterAll(async () => boards?.close());

const BLOCKS: { name: string; board: string; app: string }[] = [
  { name: "heading", board: ".page > .head", app: `${PAGE} > div:nth-child(2)` },
  { name: "outcome-tiles", board: ".page > .g6", app: `${PAGE} > [role="group"]` },
  { name: "progress-and-release", board: ".page > .card.pad", app: `${PAGE} > div:nth-child(4)` },
  { name: "review-order", board: ".page > .card:has(> .row .eyebrow)", app: `${PAGE} > div:nth-child(5)` },
  { name: "candidates", board: '.page > .card[aria-label="Candidates"]', app: `${PAGE} > section[aria-label="Candidates"]` },
  { name: "decision", board: ".page > .card.pad[style]", app: `${PAGE} > [role="group"][aria-label$="decision"]` },
];

/** Keeps the named rows of a list, in the given order, after its first `header` children. */
async function keepRows(page: Page, selector: string, header: number, names: string[]): Promise<void> {
  await page.evaluate(([sel, head, wanted]) => {
    const box = document.querySelector(sel as string);
    if (!box) throw new Error(`no ${sel}`);
    const rows = [...box.children].slice(head as number);
    const picked = (wanted as string[]).map((n) => rows.find((r) => r.textContent?.includes(n))).filter((r): r is Element => Boolean(r));
    rows.forEach((r) => r.remove());
    picked.forEach((r) => box.appendChild(r));
  }, [selector, header, names]);
}

async function pages(browser: Browser, viewport: { width: number; height: number }): Promise<{ board: Page; app: Page }> {
  const boardContext = await browser.newContext({ viewport });
  const appContext = await browser.newContext({ viewport });
  await signedInAs(appContext, org.account);
  const board = await boardContext.newPage();
  const app = await appContext.newPage();
  await openBoard(board, boards, "SittingResults");
  await board.addStyleTag({ content: ".tab:nth-child(n+6),.note,details.fold{display:none!important}" });
  await openPage(app, `/app/${org.slug}/sittings/${org.sittings.march}/results`);
  await app.locator(`${PAGE} h1`).waitFor();
  await app.getByRole("button", { name: "Open Ben Hart" }).click();
  await app.getByText("Ben Hart · the decision").waitFor();
  await keepRows(app, `${PAGE} > div:nth-child(5)`, 1, ["Chloe", "Ben"]);
  await keepRows(app, `${PAGE} > section[aria-label="Candidates"]`, 1, ["Amara", "Ben", "Chloe"]);
  await keepRows(app, `${PAGE} fieldset`, 2, ["Amara", "Dev", "Esme"]);
  await app.addStyleTag({ content: `${PAGE} [role="group"][aria-label$="decision"] a:nth-of-type(n+3){display:none!important}` });
  await app.evaluate(() => document.fonts.ready);
  return { board, app };
}

for (const viewport of VIEWPORTS) {
  test(`Sitting results matches the board, Results tab, ${viewport.name}`, async ({ browser }) => {
    const { board, app } = await pages(browser, viewport);
    for (const block of BLOCKS) {
      if (block.name === "decision") continue;
      const tab = `results-${block.name}-${viewport.name}`;
      const score = await compareRegion({ browser, boardPage: board, appPage: app, board: "SittingResults", tab, viewport: viewport.name, boardRegion: block.board, appRegion: block.app });
      console.log(`SittingResults ${tab}: ${score.percent}% largest ${JSON.stringify(score.largest)} | ${score.files.side}`);
      expect.soft(score.pass, `${tab}: ${score.percent}% differs, see ${score.files.side}`).toBe(true);
    }
  });
}

/**
 * Decision block, scored twice. Named exception (user spacing rule, DESIGN.md "Spacing rhythm"): the app stacks the
 * decision form 28px apart and 8px label to control, the board 14px and 6px. "rhythm" is the app as shipped and is
 * informational (its difference is spacing, and the rows below shift); "board-rhythm" overrides those two gaps on
 * the app side only to prove everything else (copy, controls, states) lines up, and carries the 10% bar.
 */
for (const viewport of VIEWPORTS) {
  for (const mode of ["rhythm", "board-rhythm"] as const) {
    test(`Sitting results decision ${mode}, ${viewport.name}`, async ({ browser }) => {
      const { board, app } = await pages(browser, viewport);
      if (mode === "board-rhythm") {
        // Data exception: the seed's stations are the local library's ("E2E ..."), the board's are "Chest pain history"
        // and "Breaking bad news"; rename them so the compared text is the same string.
        await app.evaluate(() => {
          const titles = ["E2E gender voice test - male patient", "E2E library station 2"];
          const names = ["Chest pain history", "Breaking bad news"];
          const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
          for (let n = walker.nextNode(); n; n = walker.nextNode()) {
            const i = titles.indexOf(n.textContent?.trim() ?? "");
            if (i >= 0 && n.textContent) n.textContent = names[i] ?? n.textContent;
          }
        });
        await app.addStyleTag({ content: `${PAGE} [role="group"][aria-label$="decision"] .gap-7{gap:12px!important} ${PAGE} [role="group"][aria-label$="decision"] .gap-2{gap:6px!important}` });
      }
      const block = BLOCKS.find((b) => b.name === "decision")!;
      const tab = `results-decision-${mode}-${viewport.name}`;
      const score = await compareRegion({ browser, boardPage: board, appPage: app, board: "SittingResults", tab, viewport: viewport.name, boardRegion: block.board, appRegion: block.app });
      console.log(`SittingResults ${tab}: ${score.percent}% largest ${JSON.stringify(score.largest)} | ${score.files.side}`);
      if (mode === "board-rhythm") expect.soft(score.percent, `${tab}: see ${score.files.side}`).toBeLessThanOrEqual(10);
    });
  }
}

/**
 * The board's dialogs (d_release, d_rel, d_back, d_prev, d_preview): each is opened on both sides and the
 * dialog box is compared (`.dlg` on the board, `[role="dialog"]` in the app). The overlay itself is not compared.
 * Named exceptions: on a phone the foundation `Modal` is a bottom sheet (user decision 2026-11-05), so the 760
 * scores are informational and the 10% bar is asserted at 1440 only; the "Result preview" body (a score of
 * "48.0 / 100" and a station list) needs a marking engine, so only its frame and copy compare.
 */
interface DialogCase {
  name: string;
  board: (page: Page) => Promise<void>;
  app: (page: Page) => Promise<void>;
}
const DIALOGS: DialogCase[] = [
  {
    name: "release-all",
    board: (p) => p.getByRole("button", { name: "Release 3 signed-off results" }).click(),
    app: (p) => p.getByRole("button", { name: /^Release 3 signed-off result/ }).click(),
  },
  {
    name: "release-two",
    board: async (p) => {
      await p.getByRole("button", { name: "Release all" }).click();
      await p.getByRole("button", { name: "Release 2 signed-off results" }).click();
    },
    app: async (p) => {
      await p.getByRole("checkbox", { name: /Esme Lowe/ }).uncheck();
      await p.getByRole("button", { name: /^Release 2 signed-off result/ }).click();
    },
  },
  {
    name: "preview-draft",
    board: (p) => p.getByRole("button", { name: "Preview what they'll see" }).first().click(),
    app: async (p) => {
      await p.getByRole("button", { name: "Open Ben Hart" }).click();
      await p.getByRole("button", { name: "Preview what they'll see" }).click();
    },
  },
  {
    name: "back-to-draft",
    board: async (p) => {
      await p.getByRole("button", { name: "Decision form" }).click();
      await p.getByRole("button", { name: "Back to draft" }).click();
    },
    app: async (p) => {
      await p.getByRole("button", { name: "Open Amara Okoye" }).click();
      await p.getByRole("button", { name: "Back to draft" }).click();
    },
  },
  {
    name: "preview-signed",
    board: async (p) => {
      await p.getByRole("button", { name: "Decision form" }).click();
      await p.getByRole("button", { name: "Preview what they'll see" }).click();
    },
    app: async (p) => {
      await p.getByRole("button", { name: "Open Amara Okoye" }).click();
      await p.getByRole("button", { name: "Preview what they'll see" }).click();
    },
  },
];

for (const viewport of VIEWPORTS) {
  for (const dialog of DIALOGS) {
    test(`Sitting results dialog ${dialog.name}, ${viewport.name}`, async ({ browser }) => {
      const boardContext = await browser.newContext({ viewport });
      const appContext = await browser.newContext({ viewport });
      await signedInAs(appContext, org.account);
      const board = await boardContext.newPage();
      const app = await appContext.newPage();
      await openBoard(board, boards, "SittingResults");
      await board.addStyleTag({ content: ".note,details.fold{display:none!important}" });
      await openPage(app, `/app/${org.slug}/sittings/${org.sittings.march}/results`);
      await app.locator(`${PAGE} h1`).waitFor();
      await dialog.board(board);
      await dialog.app(app);
      await board.locator(".dlg").waitFor();
      await app.getByRole("dialog").waitFor();
      await app.evaluate(() => document.fonts.ready);
      const tab = `dialog-${dialog.name}-${viewport.name}`;
      const score = await compareRegion({ browser, boardPage: board, appPage: app, board: "SittingResults", tab, viewport: viewport.name, boardRegion: ".dlg", appRegion: '[role="dialog"]' });
      console.log(`SittingResults ${tab}: ${score.percent}% largest ${JSON.stringify(score.largest)} | ${score.files.side}`);
      if (viewport.name === "desktop") expect.soft(score.percent, `${tab}: see ${score.files.side}`).toBeLessThanOrEqual(10);
    });
  }
}
