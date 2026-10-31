import { expect, type Locator, type Page } from "@playwright/test";
import { openPage } from "./session";

/** An iPhone-sized screen with touch, where the fixed-height layouts broke. */
export const PHONE = { viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true } as const;

/** A small Android screen, where the peer room's call and script split what little height there was. */
export const PHONE_SMALL = { viewport: { width: 360, height: 640 } } as const;

/** Thumb scrolls stop once nothing moved for this many in a row, or at the cap. */
const STILL_ROUNDS = 2;
const MAX_ROUNDS = 40;
const SCROLL_SETTLE_MS = 100;

/**
 * Scroll the way a thumb does, from the middle of the screen, until nothing
 * moves, then require `last` (by default the last piece of content in <main>) on screen.
 * The check is an IntersectionObserver, so content clipped by a box
 * that cannot scroll fails, as the station room's doctor information did.
 * Nothing may scroll sideways. An open dialog locks the scroll, so one fails at
 * once by name rather than as an unreachable end (CI once met the exam-date prompt).
 */
export async function expectReachableOnPhone(page: Page, label: string, last?: Locator): Promise<void> {
  await expect(page.getByRole("dialog"), `${label}: no dialog holds the page`).toHaveCount(0);
  const { width, height } = page.viewportSize() ?? PHONE.viewport;
  let still = 0;
  let previous = await scrolled(page);
  for (let round = 0; round < MAX_ROUNDS && still < STILL_ROUNDS; round += 1) {
    await page.mouse.move(width / 2, height / 2);
    await page.mouse.wheel(0, 1500);
    await page.waitForTimeout(SCROLL_SETTLE_MS);
    const now = await scrolled(page);
    still = now === previous ? still + 1 : 0;
    previous = now;
  }
  if (last) await expect(last, `${label}: the end of the page is reachable by scrolling`).toBeInViewport();
  else await expect.poll(() => lastContentOnScreen(page), { message: `${label}: the end of the page is reachable by scrolling` }).toBe(true);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow, `${label}: nothing scrolls sideways`).toBeLessThanOrEqual(0);
}

/** How far every scroller on the page has moved, summed: unchanged means the wheel reached the end. */
function scrolled(page: Page): Promise<number> {
  return page.evaluate(() => [...document.querySelectorAll("*")].reduce((sum, el) => sum + el.scrollTop, window.scrollY));
}

/**
 * Whether the last visible piece of content is on screen and not clipped: the page footer's when
 * the page has one after <main> (public pages: a phone-height footer pushes <main> off the top at
 * the end of the scroll), otherwise <main>'s.
 */
function lastContentOnScreen(page: Page): Promise<boolean> {
  return page.evaluate(() => {
    const main = document.querySelector("main");
    // The site footer, not a card's: the last <footer> that <main> does not contain.
    const footer = [...document.querySelectorAll("footer")].filter((el) => !main?.contains(el)).at(-1);
    const root = footer ?? main ?? document.body;
    const last = [...root.querySelectorAll("*")]
      .filter(
        (el) =>
          el.children.length === 0 &&
          el.getBoundingClientRect().height > 0 &&
          getComputedStyle(el).visibility !== "hidden" &&
          !el.closest("[aria-hidden=true], [hidden], [role=dialog]"),
      )
      .at(-1);
    // No visible leaf found: a soft "true" here would silently pass. Keep polling until it fails.
    if (!last) return false;
    return new Promise<boolean>((resolve) => {
      const observer = new IntersectionObserver(([entry]) => {
        observer.disconnect();
        resolve((entry?.intersectionRatio ?? 0) > 0);
      });
      observer.observe(last);
    });
  });
}

/** Open each path in turn and require it reachable to its end on a phone. */
export async function expectPagesReachable(page: Page, paths: readonly string[]): Promise<void> {
  for (const path of paths) {
    await openPage(page, path);
    await expectReachableOnPhone(page, path);
  }
}
