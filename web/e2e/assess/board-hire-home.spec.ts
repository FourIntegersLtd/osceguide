import { test, expect } from "@playwright/test";
import { openPage, signedInAs } from "../support/session";
import { seedHireOrg } from "../support/seed-hire";

/**
 * HireHome (docs/institution-overhaul/hire/boards/HireHome.dc.html), the hire board for /dashboard: the heading, the
 * next assessment and the employer-word ban. Its busy-state words are pinned in board-hire.spec.ts.
 * Run: E2E_REUSE_SERVER=1 npx playwright test e2e/assess/board-hire-home.spec.ts.
 */
test("Hire home shows the admin's day in employer words", async ({ page, context }) => {
  test.setTimeout(300_000);
  const org = await seedHireOrg();
  await signedInAs(context, org.account);
  await openPage(page, `/app/${org.slug}/dashboard`);

  await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
  await expect(page.getByText("Band 6 nurse assessment day").first()).toBeVisible();
  const body = page.locator("body");
  await expect(body).not.toContainText(/\bsittings?\b|\btrainees?\b|\bcircuits?\b/i);
});
