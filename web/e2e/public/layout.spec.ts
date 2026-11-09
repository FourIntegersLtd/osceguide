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
    await expect(page.locator("h1")).toContainText("Your AI patient that");
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, `the page scrolls sideways at ${width}px`).toBeLessThanOrEqual(0);
  }
});

test("the landing proof shows the copy's floor when the statistics call fails", async ({ page }) => {
  await page.route("**/site/statistics", (route) => route.abort());
  await page.goto("/");
  await expect(page.getByText("9,700+").first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Read our success stories" })).toHaveAttribute("href", "#testimonials");
  await expect(page.locator("section.bg-site-navy")).toHaveCount(0);
});

test("the landing headline is exactly two lines at every width", async ({ page }) => {
  for (const width of [320, 375, 414, 768, 1280]) {
    await page.setViewportSize({ width, height: 800 });
    await page.goto("/");
    const lines = page.locator("h1 > span[aria-hidden]");
    await expect(lines).toHaveCount(2);
    const heights = await lines.evaluateAll((els) =>
      els.map((el) => {
        const range = document.createRange();
        range.selectNodeContents(el);
        return { text: range.getBoundingClientRect().width, box: el.getBoundingClientRect().width, tall: el.getBoundingClientRect().height };
      }),
    );
    for (const line of heights) expect(line.text, `a headline line overflows at ${width}px`).toBeLessThanOrEqual(line.box);
    const h1 = await page.locator("h1").evaluate((el) => el.getBoundingClientRect().height);
    expect(h1, `the headline is not two lines at ${width}px`).toBeLessThanOrEqual(heights[0]!.tall * 2 + 2);
  }
});
