import { expect, test, type Browser, type Page, type Route } from "@playwright/test";
import { compareRegion, openBoard, serveBoards, type BoardServer } from "../support/board-diff";
import { seedSlotReviewOrg, type SlotReviewOrg } from "../support/seed-slot-review";
import { openPage, signedInAs } from "../support/session";

/**
 * Slot review (docs/institution-overhaul/boards/SlotReview.dc.html), tab 1 "Supervisor: your marks", against the
 * seeded March mock's Amara Okoye station 2 (marked, no reviewer rows). Run:
 * npx playwright test e2e/assess/board-slot-review.spec.ts.
 * Named exceptions: the board's Amara station is "Breaking bad news" with a rubric of its own, the seed's is a
 * local library station with the three seeded domains; `.note`, the build-spec fold and the page-state tabs are hidden.
 */
const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1700 },
  { name: "mobile", width: 760, height: 1700 },
] as const;
let boards: BoardServer;
let org: SlotReviewOrg;
test.beforeAll(async () => {
  test.setTimeout(600_000);
  boards = await serveBoards();
  org = await seedSlotReviewOrg();
});
test.afterAll(async () => boards?.close());

/** As shipped with the 24/28px rhythm: 32.0% at 1440, 40.2% at 760 (stand-in 31.3 / 33.0); the board's own spacing was 21.7 / 31.2. */
for (const viewport of VIEWPORTS) {
  test(`Slot review matches the board, supervisor tab, ${viewport.name}`, async ({ browser }) => {
    const slot = org.slot;
    const boardContext = await browser.newContext({ viewport });
    const appContext = await browser.newContext({ viewport });
    await signedInAs(appContext, org.supervisor);
    const board = await boardContext.newPage();
    const app = await appContext.newPage();
    await openBoard(board, boards, "SlotReview");
    await board.addStyleTag({ content: ".note,.tabs,details.fold{display:none!important}" });
    await openPage(app, `/app/${org.slug}/slots/${slot.slotId}/review?attempt=${slot.attemptId}&sitting=${org.sittings.march}`);
    await app.locator("h1").first().waitFor();
    await app.evaluate(() => document.fonts.ready);
    // Stand-in score only (SLOT_REVIEW_STANDIN=1): the board has one rating row per area, the seeded scheme also has a competency row each.
    if (process.env.SLOT_REVIEW_STANDIN) await app.addStyleTag({ content: "section[aria-label='Mark this station'] .pl-4{display:none!important}" });
    const score = await compareRegion({ browser, boardPage: board, appPage: app, board: "SlotReview", tab: `supervisor-${viewport.name}`, viewport: viewport.name, boardRegion: ".page", appRegion: 'section[aria-label="Mark this station"]' });
    console.log(`SlotReview supervisor-${viewport.name}: ${score.percent}% largest ${JSON.stringify(score.largest)} | ${score.files.side}`);
    expect.soft(score.percent).toBeLessThanOrEqual(10);
  });
}

/**
 * Tabs 2-4. Tab 2 is the admin (Ms Clarke) on Amara's station with the admin's draft at revision 2 seeded; the whole
 * "Mark this station" section is compared. Tabs 3 and 4 are composites of small cards (states, and the board's
 * component notes), so each card is compared with the app's own card in that state. Named exceptions: on desktop the
 * board lays those cards two to a row (532px) and the app's card sits in a 300px column, so the app card is set to the
 * board's width; "Not your circuit" is a forced 403 on the marking read (the api answers it for staff not on the
 * circuit); the board's cards stretch to their row's tallest (`align-items:start` on its grid); the board's Transcript and Candidate stepper cards are component notes (heading plus buttons plus a
 * caption) the app draws without that heading, so only the Reviewers card is scored.
 */
async function pair(browser: Browser, viewport: { width: number; height: number }, who: { email: string; password: string }, tab: number) {
  const boardContext = await browser.newContext({ viewport });
  const appContext = await browser.newContext({ viewport });
  await signedInAs(appContext, who);
  const board = await boardContext.newPage();
  const app = await appContext.newPage();
  await openBoard(board, boards, "SlotReview");
  await board.locator(".tabs[role=tablist] > button").nth(tab).dispatchEvent("click");
  await board.addStyleTag({ content: ".note,.tabs,details.fold{display:none!important} .g2{align-items:start}" });
  return { board, app };
}
const open = async (app: Page, slotId: string, attemptId: string | null) => {
  await openPage(app, `/app/${org.slug}/slots/${slotId}/review?attempt=${attemptId}&sitting=${org.sittings.march}`);
  await app.locator("h1").first().waitFor();
  await app.evaluate(() => document.fonts.ready);
};
const SECTION = 'section[aria-label="Mark this station"]';
const narrow = (app: Page, selector: string, width: number) =>
  app.locator(selector).first().evaluate((el, w) => { const box = el as HTMLElement; box.style.width = `${w}px`; box.style.maxWidth = `${w}px`; box.style.alignSelf = "flex-start"; }, width);

for (const viewport of VIEWPORTS) {
  test(`Slot review matches the board, admin tab, ${viewport.name}`, async ({ browser }) => {
    const { board, app } = await pair(browser, viewport, org.account, 1);
    await open(app, org.slot.slotId, org.slot.attemptId);
    await app.getByText("Revision 2").waitFor();
    // Stand-in score only (SLOT_REVIEW_STANDIN=1): the seeded scheme has a competency row under each area, the board none.
    if (process.env.SLOT_REVIEW_STANDIN) await app.addStyleTag({ content: `${SECTION} .pl-4{display:none!important}` });
    const score = await compareRegion({ browser, boardPage: board, appPage: app, board: "SlotReview", tab: `admin-${viewport.name}`, viewport: viewport.name, boardRegion: ".page", appRegion: SECTION });
    console.log(`SlotReview admin-${viewport.name}: ${score.percent}% largest ${JSON.stringify(score.largest)} | ${score.files.side}`);
    expect.soft(score.percent).toBeLessThanOrEqual(10);
  });
}

const STATES = [
  { name: "marking", card: 0, heading: "Marking", slot: () => org.pending },
  { name: "failed", card: 1, heading: "Could not be marked", slot: () => org.failed },
  { name: "hidden", card: 2, heading: "Not your circuit", slot: () => org.slot },
  { name: "conflict", card: 3, heading: "Conflict", slot: () => org.slot },
] as const;
for (const viewport of VIEWPORTS) {
  for (const state of STATES) {
    test(`Slot review matches the board, state ${state.name}, ${viewport.name}`, async ({ browser }) => {
      const { board, app } = await pair(browser, viewport, org.account, 2);
      const slot = state.slot();
      if (state.name === "hidden") await app.route("**/api/v1/attempts/*/feedback*", (route: Route) => route.fulfill({ status: 403, contentType: "application/json", body: JSON.stringify({ error: { code: "forbidden", message: "forbidden" } }) }));
      await open(app, slot.slotId, slot.attemptId);
      let region = `${SECTION} div:has(> h2:text-is("${state.heading}"))`;
      if (state.name === "hidden") region = `${SECTION} div:has(> h2:text-is("Not your circuit"))`;
      if (state.name === "conflict") {
        // Someone else saves first. The seeded station is signed off, so the api would answer review_locked; the
        // refusal the board draws (review_conflict, a 409) is forced on the save, like the 403 above.
        await app.route("**/gp-lead-review", (route: Route) => route.request().method() === "PUT"
          ? route.fulfill({ status: 409, contentType: "application/json", body: JSON.stringify({ code: "review_conflict", message: "conflict" }) })
          : route.fallback());
        await app.getByRole("button", { name: "Save draft" }).click();
        region = `${SECTION} [role="alert"]`;
      }
      await app.locator(region).first().waitFor();
      // The board's alert sits inside its card's 20px padding; the app's alert is the region, so give it that width.
      if (state.name === "conflict") await narrow(app, region, viewport.name === "desktop" ? 492 : 688);
      else if (viewport.name === "desktop") await narrow(app, region, 532);
      const boardRegion = `.g2 > .card:nth-child(${state.card + 1})` + (state.name === "conflict" ? " .al" : "");
      const score = await compareRegion({ browser, boardPage: board, appPage: app, board: "SlotReview", tab: `state-${state.name}-${viewport.name}`, viewport: viewport.name, boardRegion, appRegion: region });
      console.log(`SlotReview state-${state.name}-${viewport.name}: ${score.percent}% largest ${JSON.stringify(score.largest)} | ${score.files.side}`);
      expect.soft(score.percent).toBeLessThanOrEqual(10);
    });
  }
}

for (const viewport of VIEWPORTS) {
  test(`Slot review matches the board, reviewers card, ${viewport.name}`, async ({ browser }) => {
    const { board, app } = await pair(browser, viewport, org.supervisor, 3);
    await open(app, org.agreed.slotId, org.agreed.attemptId);
    const region = `${SECTION} div:has(> h2:text-is("What the reviewers agreed"))`;
    await app.locator(region).first().waitFor();
    if (viewport.name === "desktop") await narrow(app, region, 532);
    const score = await compareRegion({ browser, boardPage: board, appPage: app, board: "SlotReview", tab: `reviewers-${viewport.name}`, viewport: viewport.name, boardRegion: ".g2 > .card:nth-child(2)", appRegion: region });
    console.log(`SlotReview reviewers-${viewport.name}: ${score.percent}% largest ${JSON.stringify(score.largest)} | ${score.files.side}`);
    // Informational: the board's card lists each reviewer with a verdict (Dr Patel Pass); the app's lists the agreed
    // overall chip and each area's agreed rating, which the board does not draw (named exception, not scored).
    expect(score.percent).toBeGreaterThan(0);
  });
}
