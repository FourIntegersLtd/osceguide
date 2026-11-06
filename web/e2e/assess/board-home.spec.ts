import { expect, test, type Browser, type Page } from "@playwright/test";
import { ADMIN, call, login, register, stamp, switchWorkspace, PASSWORD } from "../support/api";
import { compareRegion, openBoard, serveBoards, styleDifferences, type BoardServer, type StyleCheck } from "../support/board-diff";
import { openPage, signedInAs } from "../support/session";

/**
 * Home, setup assistant (docs/institution-overhaul/boards/Main.dc.html) against the app, for the
 * board's own empty organisation: 0 exams ready, 0 published stations, 0 trainees, 1 staff.
 * Run: npx playwright test e2e/assess/board-home.spec.ts. PNGs and scores.json land in
 * docs/institution-overhaul/verify/board-diff/.
 *
 * Compared region: the page content (the board's `.page`, the app's dashboard column). The
 * sidebar is the app shell, owned by its own board and spec; it is not part of this gate.
 * The organisation is named "St Mary's" because the board's heading says "St Mary's" while its
 * sidebar says "St Mary's Medical School"; the app has one name field, so the heading wins here.
 * No mask is used: the page has no clock or avatar.
 *
 * Named exceptions (1 and 2 because the board draws a state the app only reaches with data the empty
 * organisation lacks; the app keeps its real flags and its disabled-with-reason button; nothing is removed):
 *  1. Done dots. The board ticks every earlier step as done whatever the data. Steps 2-5 are compared with the
 *     dashboard response's setup flags set done for the earlier steps (DONE_FLAGS, page.route in `pages`), so the
 *     app's real done dot and active button are rendered and diffed pixel for pixel against the board.
 *  2. Disabled "Schedule a sitting". With real flags (no exam ready) the app shows a disabled button and the reason
 *     beside it; the board's button is always active. Compared structurally in "disabled CTA" below: same geometry
 *     and type as the board's primary button, plus disabled, dimmed, with a reason and a link that fixes it.
 *  3. Half-pixel snap of the board at 760px, see `pages`. 4. Not compared, not part of the screen: the PWA install
 *     prompt and Next's dev-only badge, see `pages`.
 */
const STEPS = 5;
const SETUP = 'section[aria-label="Setup"]';
const APP_PAGE = `xpath=//section[@aria-label="Setup"]/..`;
const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1100 },
  { name: "mobile", width: 760, height: 1100 },
] as const;

let boards: BoardServer;
let account: { email: string; password: string };
let slug: string;

test.beforeAll(async () => {
  boards = await serveBoards();
  const id = stamp();
  slug = `board-${id}`;
  account = { email: `board-admin-${id}@example.com`, password: PASSWORD };
  const platform = await login(ADMIN.email, ADMIN.password);
  await call(platform, "/api/v1/platform/organizations", { method: "POST", body: { name: "St Mary's", slug, org_type: "institution" } });
  await register(account.email, "Board Admin");
  await call(platform, `/api/v1/platform/organizations/${slug}/memberships`, { method: "POST", body: { email: account.email, role: "institution_admin" } });
  await switchWorkspace(await login(account.email, PASSWORD), slug);
});
test.afterAll(async () => boards?.close());

const BOX_PROPS = ["backgroundColor", "borderTopWidth", "borderTopLeftRadius", "paddingTop", "paddingRight", "paddingBottom", "paddingLeft", "rowGap", "height"];

const STYLE_CHECKS: StyleCheck[] = [
  { name: "h1", board: "h1", app: "h1" },
  { name: "eyebrow", board: ".eyebrow", app: `xpath=//section[@aria-label="Setup"]//div[normalize-space()="Welcome"]` },
  { name: "steps card", board: ".card", app: `${SETUP} > div:nth-of-type(2)`, props: BOX_PROPS },
  { name: "current step", board: ".step.on", app: `${SETUP} ol button[aria-current="step"]` },
  { name: "step dot", board: ".step.on .dot", app: `${SETUP} ol button[aria-current="step"] > span:first-child` },
  { name: "step title", board: "h2", app: `${SETUP} h2` },
  { name: "tag chip", board: ".chip", app: `${SETUP} .self-start` },
  { name: "primary button", board: "a.btn.pri", app: `${SETUP} a:has-text("Set up an exam")` },
  { name: "secondary button", board: "a.btn:not(.pri)", app: `${SETUP} a:has-text("Browse OSCE Guide exams")` },
  { name: "why panel", board: `xpath=//div[@class="meta" and normalize-space()="Why first"]/..`, app: `xpath=//div[normalize-space()="Why first"]/..`, props: BOX_PROPS },
  { name: "help button", board: ".help", app: 'button[aria-label="How the pieces fit"]' },
  { name: "stat tile", board: ".stat", app: 'section[aria-label="At a glance"] a >> nth=0', props: BOX_PROPS },
  { name: "stat number", board: ".num", app: 'section[aria-label="At a glance"] a >> nth=0 >> span >> nth=1' },
];

/** The setup flag each step is done by, in step order. */
const DONE_FLAGS = ["programme_exam_rubric_ready", "stations_available", "trainees_added", "team_invited"] as const;
/** How many earlier steps the app's dashboard response reports as done (exception 1). */
let earlierDone = 0;

async function pages(browser: Browser, viewport: { width: number; height: number }): Promise<{ board: Page; app: Page }> {
  const boardContext = await browser.newContext({ viewport });
  const appContext = await browser.newContext({ viewport });
  await signedInAs(appContext, account);
  earlierDone = 0;
  await appContext.addInitScript(() => {
    localStorage.setItem("installPromptDismissed", "true");
    document.addEventListener("DOMContentLoaded", () => {
      const style = document.createElement("style");
      style.textContent = "nextjs-portal{display:none!important}";
      document.head.append(style);
    });
  });
  await appContext.route(/\/orgs\/[^/]+\/dashboard$/, async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    if (earlierDone > 0) {
      for (const flag of DONE_FLAGS.slice(0, earlierDone)) body.setup[flag] = true;
      body.setup.ready_to_run = true;
    }
    await route.fulfill({ response, json: body });
  });
  const board = await boardContext.newPage();
  const app = await appContext.newPage();
  await openBoard(board, boards, "Main");
  // Exception 3: below 760px the board stacks its sidebar above the page and the sidebar's height is
  // fractional (it ends at y=550.5 at 760px), so the board's text would be drawn half a pixel off the app's
  // pixel grid. The board's main top padding is reduced by that fraction; layout, sizes and colours are untouched.
  await board.evaluate(() => {
    const page = document.querySelector<HTMLElement>(".page");
    const main = document.querySelector<HTMLElement>(".main");
    const fraction = page ? (page.getBoundingClientRect().y + window.scrollY) % 1 : 0;
    if (main && fraction) main.style.setProperty("padding-top", `calc(${getComputedStyle(main).paddingTop} - ${fraction}px)`, "important");
  });
  await openPage(app, `/app/${slug}/dashboard`);
  await app.locator(SETUP).waitFor();
  await app.evaluate(() => document.fonts.ready);
  // Not part of the screen, so not compared: the PWA install prompt (small viewports; `installPromptDismissed`,
  // the flag its Close button sets, is set before the page loads) and Next's development-only "N" badge (absent in production).
  return { board, app };
}

for (const viewport of VIEWPORTS) {
  test(`Home matches Main, all five steps, ${viewport.name}`, async ({ browser }) => {
    const { board, app } = await pages(browser, viewport);
    for (let step = 0; step < STEPS; step += 1) {
      if (step > 0) {
        earlierDone = step;
        await app.reload();
        await app.locator(SETUP).waitFor();
        await app.evaluate(() => document.fonts.ready);
      }
      await board.locator(".step").nth(step).click();
      await app.locator(`${SETUP} ol button`).nth(step).click();
      await board.mouse.move(0, 0);
      await app.mouse.move(0, 0);
      const content = await compareRegion({ browser, boardPage: board, appPage: app, board: "Main", tab: `step-${step + 1}-${viewport.name}`, viewport: viewport.name, boardRegion: ".page", appRegion: APP_PAGE });
      const full = await compareRegion({ browser, boardPage: board, appPage: app, board: "Main", tab: `step-${step + 1}-${viewport.name}-fullpage`, viewport: viewport.name, boardRegion: "body", appRegion: "body" });
      console.log(`Main step ${step + 1} ${viewport.name}: content ${content.percent}% largest ${JSON.stringify(content.largest)} | full page ${full.percent}% | ${content.files.side}`);
      expect.soft(content.pass, `step ${step + 1} ${viewport.name}: ${content.percent}% differs, largest cluster ${JSON.stringify(content.largest)}, see ${content.files.side}`).toBe(true);
    }
  });
}

test("Home computed styles match Main (step 1, desktop)", async ({ browser }) => {
  const { board, app } = await pages(browser, VIEWPORTS[0]);
  const problems = await styleDifferences(board, app, STYLE_CHECKS);
  expect(problems).toEqual([]);
});

test("Home disabled CTA keeps the board's button geometry and gives its reason (exception 2, step 5, desktop)", async ({ browser }) => {
  const { board, app } = await pages(browser, VIEWPORTS[0]);
  await board.locator(".step").nth(4).click();
  await app.locator(`${SETUP} ol button`).nth(4).click();
  const geometry = ["fontFamily", "fontSize", "fontWeight", "lineHeight", "borderTopLeftRadius", "paddingTop", "paddingRight", "paddingBottom", "paddingLeft", "width", "height"];
  expect(await styleDifferences(board, app, [{ name: "schedule button", board: "a.btn.pri", app: `${SETUP} button[disabled]`, props: geometry }])).toEqual([]);
  const button = app.locator(`${SETUP} button[disabled]`);
  await expect(button).toHaveText("Schedule a sitting");
  expect(await button.evaluate((el) => getComputedStyle(el).opacity)).toBe("0.6");
  await expect(app.locator("#step-blocked")).toContainText("Nothing can be scheduled until an exam is ready.");
  await expect(app.locator("#step-blocked a")).toHaveText("Set up an exam");
});

test("Home hover states match Main (step 1, desktop)", async ({ browser }) => {
  const { board, app } = await pages(browser, VIEWPORTS[0]);
  const hovers: { tab: string; board: string; app: string }[] = [
    { tab: "hover-primary-button", board: "a.btn.pri", app: `${SETUP} a:has-text("Set up an exam")` },
    { tab: "hover-secondary-button", board: "a.btn:not(.pri)", app: `${SETUP} a:has-text("Browse OSCE Guide exams")` },
    { tab: "hover-step-row", board: ".step:not(.on) >> nth=0", app: `${SETUP} ol button:not([aria-current]) >> nth=0` },
    { tab: "hover-help-button", board: ".help", app: 'button[aria-label="How the pieces fit"]' },
  ];
  for (const h of hovers) {
    await board.locator(h.board).hover();
    await app.locator(h.app).hover();
    const score = await compareRegion({ browser, boardPage: board, appPage: app, board: "Main", tab: h.tab, viewport: "desktop", boardRegion: h.board, appRegion: h.app });
    console.log(`Main ${h.tab}: ${score.percent}% largest ${JSON.stringify(score.largest)} | ${score.files.side}`);
    expect.soft(score.pass, `${h.tab}: ${score.percent}% differs, see ${score.files.side}`).toBe(true);
  }
});
