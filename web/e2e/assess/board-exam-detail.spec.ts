import { expect, test, type Browser, type Page } from "@playwright/test";
import { MAX_DIFF_PERCENT, compareRegion, openBoard, serveBoards, type BoardServer } from "../support/board-diff";
import { createOrg } from "../support/api";
import { examsOrg, seedExamDetail, type ExamsOrg } from "../support/seed-exams";
import { openPage, signedInAs } from "../support/session";

/**
 * ExamDetail (docs/institution-overhaul/boards/ExamDetail.dc.html) and AdoptExam (AdoptExam.dc.html) against the app, at 1440 and 760.
 * Run: E2E_REUSE_SERVER=1 VERIFY_WEB_URL=http://localhost:3141 npx playwright test e2e/assess/board-exam-detail.spec.ts
 * PNGs and scores land in docs/institution-overhaul/verify/board-diff/.
 *
 * Compared region: the page content (board `.page`, the app's page root); the sidebar is the app shell.
 * Board-only design commentary (the "What changed" note, the Build spec fold) is hidden on the board side.
 *
 * EXCEPTIONS:
 *  - ExamDetail: seedExamDetail() builds the board's sample (17 stations, 16 published, two sittings, a 5 min break).
 *    Still differing: the marking scheme date is stamped by the api ("published 6 Nov", the board says "2 Oct");
 *    the app says "domains" and "Green, Amber or Red" where the board says "areas" and "Good, Fair or Poor";
 *    the platform ASPIH layout is also listed under Station layouts; the sittings carry the app's own words
 *    ("In progress" for the board's "Running", "Mock exam" for "Formal exam") and order (by date).
 *  - AdoptExam: the app's "Your programmes" list below the catalogue is a product control the board omits; hidden on
 *    the app side. Platform catalogue rows beyond the board's two (SCA, PLAB 2) are hidden on the app side.
 *  - Viewport height 2400: the app scrolls inside its shell, so an element screenshot of a long page is clipped at the viewport.
 *  - Phone: foundation sheets and drawer are kept (user decision).
 */
const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 2400 },
  { name: "mobile", width: 760, height: 2400 },
] as const;

let boards: BoardServer;

test.beforeAll(async () => {
  test.setTimeout(900_000);
  boards = await serveBoards();
  await examsOrg();
});
test.afterAll(async () => boards?.close());

async function hideBoardNotes(board: Page): Promise<void> {
  await board.evaluate(() => {
    for (const el of Array.from(document.querySelectorAll<HTMLElement>("details.fold, .note"))) el.style.display = "none";
  });
}

async function pair(browser: Browser, viewport: { width: number; height: number }, account: ExamsOrg["account"], boardName: string): Promise<{ board: Page; app: Page }> {
  const boardContext = await browser.newContext({ viewport });
  const appContext = await browser.newContext({ viewport });
  await signedInAs(appContext, account);
  const board = await boardContext.newPage();
  const app = await appContext.newPage();
  await openBoard(board, boards, boardName);
  return { board, app };
}

for (const viewport of VIEWPORTS) {
  test(`ExamDetail matches the board, ${viewport.name}`, async ({ browser }) => {
    test.setTimeout(240_000);
    const { org: fresh, examId } = await seedExamDetail();
    const { board, app } = await pair(browser, viewport, fresh.account, "ExamDetail");
    await hideBoardNotes(board);
    await openPage(app, `/app/${fresh.slug}/authoring/exams/${examId}`);
    await app.getByRole("heading", { name: "Marking scheme" }).waitFor();
    await board.mouse.move(0, 0);
    await app.mouse.move(0, 0);
    const score = await compareRegion({ browser, boardPage: board, appPage: app, board: "ExamDetail", tab: `main-${viewport.name}`, viewport: viewport.name, boardRegion: ".page", appRegion: '[data-testid="exam-detail-page"]' });
    console.log(`ExamDetail ${viewport.name}: ${score.percent}% largest ${JSON.stringify(score.largest)} | ${score.files.side}`);
    expect.soft(score.percent < MAX_DIFF_PERCENT, `ExamDetail ${viewport.name}: ${score.percent}%, see ${score.files.side}`).toBe(true);
  });

  test(`AdoptExam matches the board, ${viewport.name}`, async ({ browser }) => {
    test.setTimeout(240_000);
    const fresh = await createOrg({ prefix: "adopt", role: "institution_admin", adminName: "Board Admin" });
    const { board, app } = await pair(browser, viewport, fresh.account, "AdoptExam");
    await hideBoardNotes(board);
    await openPage(app, `/app/${fresh.slug}/programmes`);
    const scaRow = app.locator("[data-row]").filter({ hasText: "sca ·" }).first();
    await scaRow.waitFor();
    await scaRow.getByRole("button", { name: "Adopt", exact: true }).click();
    await app.getByText("is now one of your programmes").waitFor();
    await app.locator('[data-testid="your-programmes"]').evaluate((el) => { (el as HTMLElement).style.display = "none"; });
    const keep = await board.evaluate(() => Array.from(document.querySelectorAll<HTMLElement>(".page .row b")).map((b) => (b.textContent ?? "").trim()));
    // The platform lists the exam as "Simulated Consultation Assessment"; the board's sample names it "SCA".
    keep.push("Simulated Consultation Assessment");
    await app.evaluate((names) => {
      for (const row of Array.from(document.querySelectorAll<HTMLElement>("[data-row]"))) {
        const first = ((row.innerText ?? "").trim().split("\n")[0] ?? "").trim();
        if (!names.includes(first)) row.style.display = "none";
      }
    }, keep);
    // The platform lists PLAB 2 before SCA; the board lists SCA first. Board's third row (a mid-adopt state) and the
    // "Your programmes" block (its lead and New programme button are app controls) are hidden on the board side.
    // The local platform catalogue names the exam "Simulated Consultation Assessment" (api data, not seedable here); the
    // board's sample says "SCA". Only that name is rewritten on the app side, so wrapping matches; counts stay as seeded.
    await app.evaluate(() => {
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      for (let n = walker.nextNode(); n; n = walker.nextNode()) {
        if (n.nodeValue?.includes("Simulated Consultation Assessment")) n.nodeValue = n.nodeValue.replace("Simulated Consultation Assessment", "SCA");
      }
      const rows = Array.from(document.querySelectorAll<HTMLElement>("[data-row]")).filter((r) => r.style.display !== "none");
      const sca = rows.find((r) => (r.innerText ?? "").includes("sca ·"));
      if (sca) sca.parentElement?.insertBefore(sca, sca.parentElement.firstElementChild);
    });
    await board.evaluate(() => {
      const page = document.querySelector<HTMLElement>(".page");
      const rows = Array.from(page?.querySelectorAll<HTMLElement>(".row") ?? []);
      const ortho = rows.find((r) => (r.textContent ?? "").includes("Orthopaedics"));
      ortho?.remove();
      const cards = Array.from(page?.children ?? []) as HTMLElement[];
      const idx = cards.findIndex((c) => (c.textContent ?? "").trim() === "Your programmes");
      if (idx >= 0) { cards[idx]!.style.display = "none"; cards[idx + 1]!.style.display = "none"; }
    });
    await board.mouse.move(0, 0);
    await app.mouse.move(0, 0);
    const score = await compareRegion({ browser, boardPage: board, appPage: app, board: "AdoptExam", tab: `main-${viewport.name}`, viewport: viewport.name, boardRegion: ".page", appRegion: '[data-testid="programmes-page"]' });
    console.log(`AdoptExam ${viewport.name}: ${score.percent}% largest ${JSON.stringify(score.largest)} | ${score.files.side}`);
    expect.soft(score.percent < MAX_DIFF_PERCENT, `AdoptExam ${viewport.name}: ${score.percent}%, see ${score.files.side}`).toBe(true);
  });
}
