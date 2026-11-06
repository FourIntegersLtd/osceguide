import { expect, test, type Browser, type Page } from "@playwright/test";
import { compareRegion, openBoard, serveBoards, type BoardServer } from "../support/board-diff";
import { seedPeopleOrg, type PeopleOrg } from "../support/seed-people";
import { seedInvitationToken } from "../support/seed-invitation";
import { signedInAs } from "../support/session";

/**
 * SignIn, AcceptInvite and RegisterOrg (docs/institution-overhaul/boards/) against the signed-out screens.
 * Run: E2E_REUSE_SERVER=1 VERIFY_WEB_URL=http://localhost:3177 npx playwright test e2e/assess/board-auth.spec.ts
 * PNGs and scores.json land in docs/institution-overhaul/verify/board-diff/.
 *
 * Compared region: the card (the board's `.card.pad`, the app's `main section`). The board's logo row and tab strip
 * are design navigation and the app's own header, footer and navy quote panel sit outside the card.
 *
 * Named exceptions:
 *  1. Input text. The boards show sample values (okafor@stmarys.ac.uk, dots, placeholders); the app's boxes are empty.
 *     Text colour and placeholders are transparent on both sides.
 *  2. Sign in: the SSO button and its "requires single sign-on" alert are alternatives the app draws only on a host an
 *     organisation has claimed (none on localhost); display:none on the board. The app keeps "Don't have an account?
 *     Create account" and the show-password eye, which the board does not draw (nothing that exists may disappear).
 *  3. Accept invitation: the api tells the page the organisation's name only, not who invited or as what, so the line
 *     under the title is "<org> has invited you. Choose a password to join." where the board says "Dr Okafor invited
 *     you as a trainee. Choose a password to accept." The app also keeps the password rule hint and the eye.
 *     The board's "You are in" tab is a landing the app does not have (accepting signs you in and goes to /app).
 *  4. Forms keep their visible labels ("New password", "Confirm it"); the board's two password boxes carry placeholders only.
 *  5. Register organisation: the board has "Mock OSCEs" ticked, so the app ticks it. "Sent" posts to /site/messages,
 *     which the spec answers itself so no message reaches staff.
 *  6. Elements the app keeps and the board omits are marked `data-auth-extra` and hidden in the app capture: the password rule
 *     hint, the show-password eye on the reset and accept screens, and the "Sign in" / "Remembered it?" links under a card.
 *     Without that, one extra line shifts every row below it. Sign in itself is scored with its eye and extra link in place.
 *  7. Not scored here: "Choose a new password" after a temporary password (/change-password) is Settings' ChangePassword card, scored
 *     with Your account in board-settings.spec.ts; Two-step sign-in and the SSO callback need an account with 2FA / a claimed host.
 *  8. Board design notes and the build-spec fold are display:none.
 */
const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1100 },
  { name: "mobile", width: 760, height: 1100 },
] as const;
const CARD = "main section";

let boards: BoardServer;
let org: PeopleOrg;
let inviteToken = "";

test.beforeAll(async () => {
  test.setTimeout(180_000);
  boards = await serveBoards();
  org = await seedPeopleOrg();
  inviteToken = await seedInvitationToken(org);
});
test.afterAll(async () => boards?.close());

const HIDE_BOARD = `.note,details.fold{display:none!important}input.input,textarea.input{color:transparent!important}input::placeholder,textarea::placeholder{color:transparent!important}`;
const HIDE_APP = `[data-auth-extra],input[autocomplete="new-password"]~p[id$="-hint"],div:has(>input[autocomplete="new-password"])~p[id$="-hint"]{display:none!important}input,textarea{color:transparent!important}input::placeholder,textarea::placeholder{color:transparent!important}`;

interface Setup {
  board: string;
  boardTab: number;
  /** The board card, by position among the tab's `.card.pad`. */
  boardCard: number;
  path: string;
  signedIn?: boolean;
  hideBoard?: string;
  /** Runs on the app once loaded (ticks a box, submits). */
  prepare?: (app: Page) => Promise<void>;
  /** Runs on the board once the tab is chosen. */
  prepareBoard?: (board: Page) => Promise<void>;
}

async function pages(browser: Browser, viewport: { width: number; height: number }, setup: Setup): Promise<{ board: Page; app: Page }> {
  const boardContext = await browser.newContext({ viewport });
  const appContext = await browser.newContext({ viewport });
  // The cookie dialog is the app's, not the card's.
  await appContext.addInitScript(() => { localStorage.setItem("analytics-consent", "rejected"); localStorage.setItem("installPromptDismissed", "true"); });
  if (setup.signedIn) await signedInAs(appContext, org.account);
  const board = await boardContext.newPage();
  const app = await appContext.newPage();
  await openBoard(board, boards, setup.board);
  await board.addStyleTag({ content: HIDE_BOARD + (setup.hideBoard ?? "") });
  await board.locator(".tabs .tab").nth(setup.boardTab).click();
  await setup.prepareBoard?.(board);
  await app.goto(setup.path, { waitUntil: "domcontentloaded" });
  await app.locator(CARD).first().waitFor();
  await app.evaluate(() => document.fonts.ready);
  await app.addStyleTag({ content: HIDE_APP });
  // A submit is inert until React owns the form.
  await app.waitForFunction(() => !document.querySelector('main section button[type="submit"]:disabled'));
  await setup.prepare?.(app);
  return { board, app };
}

const SETUPS: Record<string, Setup> = {
  "SignIn:signin": {
    board: "SignIn", boardTab: 0, boardCard: 0, path: "/login",
    // Exception 2.
    hideBoard: ".card.pad>a.btn:not(.pri),.card.pad>.al{display:none!important}",
  },
  "SignIn:forgot": { board: "SignIn", boardTab: 2, boardCard: 0, path: "/forgot-password" },
  "SignIn:reset": { board: "SignIn", boardTab: 2, boardCard: 1, path: "/reset-password?token=board" },
  "AcceptInvite:invitation": { board: "AcceptInvite", boardTab: 0, boardCard: 0, path: `/accept-invitation?token=${"TOKEN"}` },
  "AcceptInvite:incomplete": { board: "AcceptInvite", boardTab: 2, boardCard: 0, path: "/accept-invitation" },
  "RegisterOrg:form": {
    board: "RegisterOrg", boardTab: 0, boardCard: 0, path: "/register/organisation",
    // Exception 5.
    prepare: async (app) => void (await app.getByLabel("Mock OSCEs").check({ force: true })),
  },
  "RegisterOrg:sent": {
    board: "RegisterOrg", boardTab: 1, boardCard: 0, path: "/register/organisation",
    prepare: async (app) => {
      await app.route("**/site/messages*", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ id: "board", status: "received" }) }));
      await app.getByLabel("Mock OSCEs").check({ force: true });
      await app.getByLabel("Organisation name").fill("St Mary's Medical School");
      await app.getByLabel("Your name").fill("Dr Okafor");
      await app.getByLabel("Work email").fill("okafor@stmarys.example.com");
      await app.getByRole("button", { name: "Request set-up" }).click();
      await app.getByRole("heading", { name: "Request received" }).waitFor();
    },
  },
};

for (const [key, setup] of Object.entries(SETUPS)) {
  for (const viewport of VIEWPORTS) {
    test(`${key} matches ${setup.board}, ${viewport.name}`, async ({ browser }) => {
      const resolved = { ...setup, path: setup.path.replace("TOKEN", inviteToken) };
      const { board, app } = await pages(browser, viewport, resolved);
      await app.mouse.move(0, 0);
      await board.mouse.move(0, 0);
      const s = await compareRegion({
        browser, boardPage: board, appPage: app, board: setup.board, tab: `${key.split(":")[1]}-${viewport.name}`, viewport: viewport.name,
        boardRegion: `.card.pad >> nth=${setup.boardCard}`, appRegion: CARD,
      });
      console.log(`${key} ${viewport.name}: ${s.percent}% largest ${JSON.stringify(s.largest)} | ${s.files.side}`);
      expect.soft(s.pass, `${key} ${viewport.name}: ${s.percent}% differs, see ${s.files.side}`).toBe(true);
    });
  }
}
