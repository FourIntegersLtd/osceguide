import type { Browser, Page } from "@playwright/test";
import { compareRegion, openBoard, type BoardServer } from "./board-diff";
import type { TraineeOrg } from "./seed-trainee";
import { personAccount } from "./seed-trainee";
import { openPage, signedInAs } from "./session";

export const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1700 },
  { name: "mobile", width: 760, height: 1700 },
] as const;

/**
 * A board page and an app page signed in as one seeded person. JoinRoom enters the room on load (it must, during
 * reading) and there is no LiveKit here, so the token request is held: the hero stays at its first frame (the
 * spinner Join button) instead of becoming the room's "Connecting the patient".
 */
export async function traineePages(
  browser: Browser,
  boards: BoardServer,
  org: TraineeOrg,
  boardName: string,
  viewport: { width: number; height: number },
  person: number,
): Promise<{ board: Page; app: Page }> {
  const boardContext = await browser.newContext({ viewport });
  const appContext = await browser.newContext({ viewport });
  await signedInAs(appContext, personAccount(org, person));
  const board = await boardContext.newPage();
  const app = await appContext.newPage();
  await app.route("**/join-token", () => undefined);
  await openBoard(board, boards, boardName);
  return { board, app };
}

/** Hide the board's own annotations (tab strip, note, build-spec fold); call after the last tab click. */
export const hideAnnotations = (board: Page) => board.addStyleTag({ content: ".tabs,.note,details.fold{display:none!important}" });

export interface TraineeTab {
  index: number;
  key: string;
  person: number;
  /** Path under `/app/<slug>`. */
  path: (org: TraineeOrg) => string;
  /** Text that says the app screen has loaded. */
  ready: string | RegExp;
}

/** Open one board tab and the matching app screen, compare `.page` against the app's labelled section, log the score. */
export async function scoreTab(
  browser: Browser,
  boards: BoardServer,
  org: TraineeOrg,
  boardName: string,
  label: string,
  tab: TraineeTab,
  viewport: (typeof VIEWPORTS)[number],
): Promise<{ app: Page; score: Awaited<ReturnType<typeof compareRegion>> }> {
  const { board, app } = await traineePages(browser, boards, org, boardName, viewport, tab.person);
  await board.locator(".tab").nth(tab.index).click();
  await hideAnnotations(board);
  await openPage(app, `/app/${org.slug}${tab.path(org)}`);
  await app.getByText(tab.ready).first().waitFor();
  await app.evaluate(() => document.fonts.ready);
  await app.mouse.move(0, 0);
  const name = `tab-${tab.index + 1}-${tab.key}-${viewport.name}`;
  const score = await compareRegion({ browser, boardPage: board, appPage: app, board: boardName, tab: name, viewport: viewport.name, boardRegion: ".page", appRegion: `section[aria-label="${label}"]` });
  console.log(`${boardName} ${name}: ${score.percent}% largest ${JSON.stringify(score.largest)} | ${score.files.side}`);
  return { app, score };
}
