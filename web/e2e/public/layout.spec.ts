import { expect, test } from "@playwright/test";
import { PUBLIC_MARKETING_PATHS } from "../../src/foundation/routing/pathVisibility";

/**
 * Every public page wears the shared chrome (the real logo linking home, a
 * navigation and a footer) and fits a 320px phone. A page left out of
 * `SiteShell` once shipped /blogs and /pricing with no logo, nav or footer.
 */
test.use({ viewport: { width: 320, height: 800 } });

for (const path of PUBLIC_MARKETING_PATHS) {
  test(`chrome and 320px fit ${path || "/"}`, async ({ page }) => {
    await page.goto(path || "/");
    await expect(page.locator("a[aria-label$='OSCE Guide home']").first()).toBeVisible();
    await expect(page.getByRole("navigation").first()).toBeVisible();
    await expect(page.getByRole("contentinfo")).toHaveCount(1);
    const widths = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, inner: window.innerWidth }));
    expect(widths.scroll, `${path} scrolls sideways`).toBeLessThanOrEqual(widths.inner);
  });
}

test("the landing has one headline and no horizontal scroll at every width", async ({ page }) => {
  for (const width of [320, 390, 768, 1280]) {
    await page.setViewportSize({ width, height: 800 });
    await page.goto("/");
    await expect(page.locator("h1")).toHaveCount(1);
    await expect(page.locator("h1")).toContainText("Practise your exam cases out loud with an AI patient.");
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, `the page scrolls sideways at ${width}px`).toBeLessThanOrEqual(0);
  }
});

test("the landing proof line is hidden when the statistics call fails", async ({ page }) => {
  await page.route("**/site/statistics", (route) => route.abort());
  await page.goto("/");
  await expect(page.locator("h1")).toHaveCount(1);
  await page.waitForTimeout(1500);
  await expect(page.getByText("cases marked so far")).toHaveCount(0);
  await expect(page.locator("section.bg-site-navy")).toHaveCount(1);
});
