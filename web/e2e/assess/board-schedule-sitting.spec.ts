import { expect, test, type Browser, type Page } from "@playwright/test";
import { call } from "../support/api";
import {
  compareRegion,
  openBoard,
  serveBoards,
  styleDifferences,
  type BoardServer,
  type StyleCheck,
} from "../support/board-diff";
import { STATION_CONTENT } from "../support/seed-exams";
import { seedSittingsOrg, type SittingsOrg } from "../support/seed-sittings";
import { unlinkAccount } from "../support/seed-people";
import { openPage, signedInAs } from "../support/session";

/**
 * Schedule a sitting (docs/institution-overhaul/boards/ScheduleSitting.dc.html) against the app, every step of
 * both kinds, desktop (1440) and mobile (760). The board has no dialog; the app's "Add from this exam" box is
 * checked app-only below. Run: npx playwright test e2e/assess/board-schedule-sitting.spec.ts --grep "<state>".
 * PNGs and scores.json land in docs/institution-overhaul/verify/board-diff/.
 *
 * Compared region: the step strip plus the content row (`.strip` and `.wrap` on the board, the strip and content
 * wrapper in the app, both 1072px wide). The top bar is full width on the board and is compared by computed style
 * only (exception 1). The sidebar is the app shell and is not part of this gate. No mask is used.
 *
 * User rules that override the board (named, scored in the run output; see scores.json):
 *  A. Spacing rhythm: 8px label to control, 28px between fields, 16px between option cards, 32px above the footer
 *     divider (assessForm* tokens). The board uses 6px/18px/gap 24, so cards and the footer are taller by design.
 *  B. Selection and focus: 1px light blue (--assess-select-border) on the current step dot, the chosen option card
 *     and checked boxes; the board's saturated #1D4ED8 fill on a checked box and 5px radio ring is kept as drawn.
 * Data-driven differences (the api or the seed cannot show the board's text):
 *  1. Top bar: compared by styleDifferences, not pixels (it is full width, outside the content region).
 *  2. Date is a native date input ("2026-11-26" drawn by the browser) against the board's text "26 Nov 2026".
 *  3. Station kind ("History and examination") is not on a picked station, so the board's grey kind column is absent.
 *  4. The board's "Group: Firm B" row is a roster person here ("Neil Foster"); groups are on the Groups tab.
 *  5. Candidate count: the roster has 7 people, Daniel has not joined, so a formal sitting picks 6 (the board's 7 is 3
 *     people plus its "Group: Firm B" row of 4, which the app lists as people). supervisor-each picks 3 because the
 *     board lists 3 and "and 4 more" while the app lists every candidate. The people list is therefore 2 rows longer
 *     than the board's 5 (people-formal/training only pass with the stand-in below).
 *  6. A not-joined row says "Can't be scheduled until they accept." (no invite date, the roster read has none).
 *  7. Supervisor options read "email (role)": the membership read has no display name.
 *  8. Number inputs show "3", the board's inputs show "3 min" as text.
 *  9. Training has no breaks (domain_run), so the board's Breaks block is hidden on the board side of timing-training.
 *  10. "Ends about" is computed (10:38); the board draws 10:41.
 *  11. (closed: training picks 6 stations and 6 trainees, as the board.)
 *  12. Back on step 1 is a link to Sittings (the board's Back is inert there).
 *  13. "Add a break after" select beside "Add a break" (the board's button has no way to choose the gap).
 *  14. (closed: see 11.)
 * Scores as shipped, desktop 1440 / mobile 760 (the only ones that count), then the scoring-only STAND-IN (the app's
 * gap-7/gap-2/gap-4 rhythm and footer divider swapped for the board's 18/6/10px and none, plus the two extra people
 * rows hidden on the people step; logged as "STAND-IN", never asserted):
 *  basics-formal 13.7/12.7 -> 7.8/8.6     stations-formal 8.9    stations-training 9.0/7.0
 *  people-formal 22.5/22.2 -> 8.7/3.3 (5)   people-training 22.7/22.3 -> 4.2/3.7 (5)
 *  timing-formal 16.8/16.4 -> 7.1/7.2     timing-training 16.7/14.8 -> 6.1/5.0 (9)
 *  supervisor-one 14.3/12.9 -> 6.9/6.5    supervisor-each 5.8   review-formal 6.3   review-training 7.8
 * Still over 10% as shipped: only the user's rhythm (A, B) and the people row count (5), measured by the stand-in.
 */
const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1100 },
  { name: "mobile", width: 760, height: 1100 },
] as const;
const TITLES = [
  "Chest pain in a 54-year-old",
  "Breaking bad news",
  "Diabetic foot review",
  "Consent for endoscopy",
  "Paediatric asthma",
  "Prescribing: warfarin",
];
const BOARD_REGION = "#cmp";
const APP_REGION = `xpath=//nav[@aria-label="Steps"]/..`;
const STAND_IN_SCOPE = "main";

let boards: BoardServer;
let org: SittingsOrg;

test.beforeAll(async () => {
  boards = await serveBoards();
  org = await seedSittingsOrg({
    adminName: "Dr Okafor",
    trainees: 7,
    names: [
      "Aisha Bello",
      "Tom Hughes",
      "Priya Nair",
      "Daniel Osei",
      "Neil Foster",
      "Grace Adeyemi",
      "Omar Haddad",
    ],
    supervisors: ["Dr Patel", "Ms Clarke"],
  });
  // The wizard offers the exam's own published stations: six of them, named as on the board.
  for (const title of TITLES) {
    const made = await call<{ id: string }>(
      org.token,
      `/api/v1/orgs/${org.slug}/stations`,
      {
        method: "POST",
        body: {
          title,
          exam_code: "finals",
          content: { title, ...STATION_CONTENT },
        },
      },
    );
    await call(
      org.token,
      `/api/v1/orgs/${org.slug}/stations/${made.id}/versions/1/publish`,
      { method: "POST" },
    );
  }
  // The board offers two exams: retire the third. Daniel Osei has not accepted his invitation.
  await call(
    org.token,
    `/api/v1/orgs/${org.slug}/programmes/${org.exams.year3.programmeId}`,
    { method: "PATCH", body: { status: "retired" } },
  );
  const daniel = org.people[3];
  if (daniel) unlinkAccount(org.slug, daniel.email);
});
test.afterAll(async () => boards?.close());

type Kind = "exam" | "training";
type Target = { step: number; kind: Kind; each?: boolean };

async function pages(
  browser: Browser,
  viewport: { width: number; height: number },
): Promise<{ board: Page; app: Page }> {
  const boardContext = await browser.newContext({ viewport });
  const appContext = await browser.newContext({ viewport });
  await signedInAs(appContext, org.account);
  await appContext.addInitScript(() => {
    localStorage.setItem("installPromptDismissed", "true");
    document.addEventListener("DOMContentLoaded", () => {
      const style = document.createElement("style");
      style.textContent = "nextjs-portal{display:none!important}";
      document.head.append(style);
    });
  });
  const board = await boardContext.newPage();
  const app = await appContext.newPage();
  await openBoard(board, boards, "ScheduleSitting");
  await wrapRegion(board);
  await openPage(app, `/app/${org.slug}/sittings/new`);
  await app.getByRole("textbox", { name: "Name" }).waitFor();
  await app.evaluate(() => document.fonts.ready);
  return { board, app };
}

/** Region: the strip and the content row, as one 1072px column. The board re-renders on a click, so this runs again after. */
async function wrapRegion(board: Page): Promise<void> {
  await board.evaluate(() => {
    if (document.getElementById("cmp")) return;
    const strip = document.querySelector(".strip");
    const wrap = document.querySelector(".wrap");
    const box = document.createElement("div");
    box.id = "cmp";
    box.style.cssText = "display:flow-root;max-width:1072px;margin:0 auto";
    strip?.before(box);
    if (strip && wrap) box.append(strip, wrap);
    document
      .querySelector<HTMLElement>("details.fold")
      ?.parentElement?.style.setProperty("display", "none");
  });
}

const continueBoard = (board: Page) =>
  board.getByRole("button", { name: "Continue" }).click();
const continueApp = (app: Page) =>
  app.getByRole("button", { name: "Continue" }).click();

/** Drives the real wizard to the target step, and the board to the same one. */
async function reach(board: Page, app: Page, target: Target): Promise<void> {
  const training = target.kind === "training";
  if (training) await board.locator(".opt").nth(1).click();
  await app
    .getByRole("radio", { name: training ? /^Training/ : /^Formal exam/ })
    .click();
  await app.getByRole("textbox", { name: "Name" }).fill("Summer finals");
  await app
    .locator("#sitting-exam")
    .selectOption({ label: "Final-year OSCE · Ready to schedule" });
  await app.locator("#sitting-date").fill("2026-11-26");
  await app.locator("#sitting-year").selectOption({ label: "Final year 2026" });
  for (let step = 1; step <= target.step; step += 1) {
    // Move on from the previous step, then fill this one in the app (the board shows it filled already).
    await continueApp(app);
    await continueBoard(board);
    if (step === 1) await pickStations(app, 6);
    if (step === 2) await pickPeople(app, target.each ? 3 : 6);
    if (step === 3 && !training) await addBreaks(app);
    if (step === 4) await chooseSupervisors(app, target);
  }
}

async function pickStations(app: Page, count: number): Promise<void> {
  await app.getByRole("button", { name: "Add from this exam" }).click();
  const dialog = app.getByRole("dialog");
  for (const title of TITLES.slice(0, count)) {
    await dialog
      .locator("li, tr, article, div")
      .filter({ hasText: title })
      .getByRole("button", { name: "Add", exact: true })
      .last()
      .click();
  }
  await dialog.getByRole("button", { name: "Done" }).click();
}

async function pickPeople(app: Page, count: number): Promise<void> {
  const boxes = app.getByRole("checkbox");
  for (let n = 0; n < count; n += 1) await boxes.nth(n).check({ force: true });
}

async function addBreaks(app: Page): Promise<void> {
  await app.getByLabel("Add a break after").selectOption("2");
  await app.getByRole("button", { name: "Add a break" }).click();
  await app.getByLabel("Add a break after").selectOption("4");
  await app.getByRole("button", { name: "Add a break" }).click();
  await app.getByLabel("Break length after station 4").fill("15");
}

async function chooseSupervisors(app: Page, target: Target): Promise<void> {
  const patel = { label: /Dr Patel|drpatel/ };
  if (target.kind === "training") return;
  if (target.each) {
    await app
      .getByRole("radio", { name: /^A supervisor per candidate/ })
      .click();
    const selects = app.getByRole("combobox", { name: /^Supervisor for/ });
    for (let n = 0; n < (await selects.count()); n += 1)
      await selects.nth(n).selectOption({ index: 1 + (n % 2) });
  } else {
    const option = app
      .locator("#sitting-supervisor option")
      .filter({ hasText: patel.label });
    await app
      .locator("#sitting-supervisor")
      .selectOption({ label: (await option.first().textContent()) ?? "" });
  }
}

const STATES: { tab: string; target: Target }[] = [
  { tab: "basics-formal", target: { step: 0, kind: "exam" } },
  { tab: "basics-training", target: { step: 0, kind: "training" } },
  { tab: "stations-formal", target: { step: 1, kind: "exam" } },
  { tab: "stations-training", target: { step: 1, kind: "training" } },
  { tab: "people-formal", target: { step: 2, kind: "exam" } },
  { tab: "people-training", target: { step: 2, kind: "training" } },
  { tab: "timing-formal", target: { step: 3, kind: "exam" } },
  { tab: "timing-training", target: { step: 3, kind: "training" } },
  { tab: "supervisor-one", target: { step: 4, kind: "exam" } },
  { tab: "supervisor-each", target: { step: 4, kind: "exam", each: true } },
  { tab: "review-formal", target: { step: 5, kind: "exam" } },
  { tab: "review-training", target: { step: 5, kind: "training" } },
];

for (const viewport of VIEWPORTS) {
  for (const state of STATES) {
    test(`Schedule a sitting ${state.tab} matches ScheduleSitting, ${viewport.name}`, async ({
      browser,
    }) => {
      const { board, app } = await pages(browser, viewport);
      await reach(board, app, state.target);
      if (state.target.each) await board.locator(".opt").nth(1).click();
      await wrapRegion(board);
      await app.evaluate(() =>
        (document.activeElement as HTMLElement | null)?.blur(),
      );
      // Exception 9: the board draws a Breaks block that a training sitting does not have (domain_run).
      if (state.tab === "timing-training")
        await board.addStyleTag({
          content: `${BOARD_REGION} div[style*="border-top:1px solid #EFEFF2"]{display:none!important}`,
        });
      await board.mouse.move(0, 0);
      await app.mouse.move(0, 0);
      const score = await compareRegion({
        browser,
        boardPage: board,
        appPage: app,
        board: "ScheduleSitting",
        tab: `${state.tab}-${viewport.name}`,
        viewport: viewport.name,
        boardRegion: BOARD_REGION,
        appRegion: APP_REGION,
      });
      console.log(
        `ScheduleSitting ${state.tab} ${viewport.name}: ${score.percent}% largest ${JSON.stringify(score.largest)} | ${score.files.side}`,
      );
      expect
        .soft(
          score.pass,
          `${state.tab} ${viewport.name}: ${score.percent}% differs, see ${score.files.side}`,
        )
        .toBe(true);
      // Scoring-only stand-in, never a pass: the user's ample spacing (assess form tokens) swapped for the board's
      // 6px/18px/10px rhythm, and on the people step the two roster rows the board folds into its Group row hidden.
      await app.addStyleTag({
        content: `${STAND_IN_SCOPE} .gap-7{gap:18px!important} ${STAND_IN_SCOPE} .gap-2{gap:6px!important} ${STAND_IN_SCOPE} .grid.gap-4{gap:10px!important} ${STAND_IN_SCOPE} .border-t.pt-8{border-top-width:0!important;padding-top:0!important;margin-top:0!important}${
          state.tab.startsWith("people")
            ? ` ${STAND_IN_SCOPE} ul li:nth-child(n+6){display:none!important}`
            : ""
        }`,
      });
      const standIn = await compareRegion({
        browser,
        boardPage: board,
        appPage: app,
        board: "ScheduleSitting",
        tab: `${state.tab}-${viewport.name}-standin`,
        viewport: viewport.name,
        boardRegion: BOARD_REGION,
        appRegion: APP_REGION,
      });
      console.log(
        `ScheduleSitting ${state.tab} ${viewport.name} STAND-IN: ${standIn.percent}% largest ${JSON.stringify(standIn.largest)} | ${standIn.files.side}`,
      );
    });
  }
}

const STYLE_CHECKS: StyleCheck[] = [
  {
    name: "top bar",
    board: ".top",
    app: `xpath=//a[normalize-space()="Close"]/..`,
    props: [
      "backgroundColor",
      "borderBottomWidth",
      "paddingTop",
      "paddingBottom",
      "paddingLeft",
      "paddingRight",
      "height",
    ],
  },
  {
    name: "close button",
    board: ".top a.btn",
    app: `xpath=//a[normalize-space()="Close"]`,
    props: ["fontSize", "fontWeight", "borderTopLeftRadius", "height"],
  },
  {
    name: "h1",
    board: "h1",
    app: "h2",
    props: ["fontSize", "fontWeight", "lineHeight", "color"],
  },
  {
    name: "label",
    board: "label",
    app: "label",
    props: ["fontSize", "fontWeight", "color"],
  },
  {
    name: "input",
    board: ".input",
    app: "#sitting-name",
    props: [
      "fontSize",
      "borderTopLeftRadius",
      "height",
      "paddingLeft",
      "color",
      "backgroundColor",
    ],
  },
  {
    name: "primary button",
    board: ".btn.pri",
    app: `button:has-text("Continue")`,
    props: [
      "fontSize",
      "fontWeight",
      "borderTopLeftRadius",
      "height",
      "paddingLeft",
      "backgroundColor",
      "color",
    ],
  },
];

test("Schedule a sitting computed styles match ScheduleSitting (step 1, desktop)", async ({
  browser,
}) => {
  const { board, app } = await pages(browser, VIEWPORTS[0]);
  expect(await styleDifferences(board, app, STYLE_CHECKS)).toEqual([]);
});

test("Schedule a sitting add-stations dialog (app only: the board has no dialog)", async ({
  browser,
}) => {
  const { app } = await pages(browser, VIEWPORTS[0]);
  await app.getByRole("textbox", { name: "Name" }).fill("Summer finals");
  await continueApp(app);
  await app.getByRole("button", { name: "Add from this exam" }).click();
  const dialog = app.getByRole("dialog");
  await expect(dialog).toContainText(TITLES[0] ?? "");
  await dialog.screenshot({
    path: "../docs/institution-overhaul/verify/board-diff/ScheduleSitting-add-stations-dialog.app.png",
  });
  await dialog.getByRole("button", { name: "Done" }).click();
  await expect(dialog).toBeHidden();
});

test("Schedule a sitting with no exam ready (app only: the board has no such state)", async ({
  browser,
}) => {
  const programmes = Object.values(org.exams).map((exam) => exam.programmeId);
  const set = (status: string) =>
    Promise.all(
      programmes.map((id) =>
        call(org.token, `/api/v1/orgs/${org.slug}/programmes/${id}`, {
          method: "PATCH",
          body: { status },
        }),
      ),
    );
  await set("draft");
  try {
    const context = await browser.newContext({ viewport: VIEWPORTS[0] });
    await signedInAs(context, org.account);
    const app = await context.newPage();
    await app.goto(`/app/${org.slug}/sittings/new`);
    await expect(app.getByText("No exam is ready to schedule")).toBeVisible();
    await app.screenshot({
      path: "../docs/institution-overhaul/verify/board-diff/ScheduleSitting-no-exam-ready.app.png",
    });
  } finally {
    await set("active");
    await call(
      org.token,
      `/api/v1/orgs/${org.slug}/programmes/${org.exams.year3.programmeId}`,
      { method: "PATCH", body: { status: "retired" } },
    );
  }
});
