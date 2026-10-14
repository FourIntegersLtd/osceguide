import { expect, type Locator, type Page } from "@playwright/test";
import { openPage } from "./session";

/** An iPhone-sized screen with touch, where the fixed-height layouts broke. */
export const PHONE = { viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true } as const;

/** A small Android screen, where the peer room's call and script split what little height there was. */
export const PHONE_SMALL = { viewport: { width: 360, height: 640 } } as const;

/** Thumb scrolls before checking the end: enough for the longest page in the sweep. */
const SCROLL_ROUNDS = 20;
const SCROLL_SETTLE_MS = 100;

/**
 * Scroll the way a thumb does, from the middle of the screen, until nothing
 * moves, then require `last` (by default the last piece of content in <main>)
 * on screen. The check is an IntersectionObserver, so content clipped by a box
 * that cannot scroll fails, as the station room's doctor information did.
 * Nothing may scroll sideways.
 */
export async function expectReachableOnPhone(page: Page, label: string, last?: Locator): Promise<void> {
  const { width, height } = page.viewportSize() ?? PHONE.viewport;
  for (let round = 0; round < SCROLL_ROUNDS; round += 1) {
    await page.mouse.move(width / 2, height / 2);
    await page.mouse.wheel(0, 1500);
    await page.waitForTimeout(SCROLL_SETTLE_MS);
  }
  if (last) await expect(last, `${label}: the end of the page is reachable by scrolling`).toBeInViewport();
  else await expect.poll(() => lastContentOnScreen(page), { message: `${label}: the end of the page is reachable by scrolling` }).toBe(true);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow, `${label}: nothing scrolls sideways`).toBeLessThanOrEqual(0);
}

/** Whether the last visible piece of content in <main> is on screen and not clipped. */
function lastContentOnScreen(page: Page): Promise<boolean> {
  return page.evaluate(() => {
    const root = document.querySelector("main") ?? document.body;
    const last = [...root.querySelectorAll("*")]
      .filter(
        (el) =>
          el.children.length === 0 &&
          el.getBoundingClientRect().height > 0 &&
          getComputedStyle(el).visibility !== "hidden" &&
          !el.closest("[aria-hidden=true], [hidden], [role=dialog]"),
      )
      .at(-1);
    if (!last) return true;
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
