import { test, expect } from "@playwright/test";
import { openPage, signedInAs } from "../support/session";
import { seedHireOrg } from "../support/seed-hire";

/**
 * HireHome (docs/institution-overhaul/hire/boards/HireHome.dc.html), the hire board for /dashboard, busy state.
 *
 * The redesigned board draws its three states (first-run rail, busy day, quiet day) in one page behind a state
 * switcher, which the pixel-diff runner (board-diff.ts) does not drive, so this spec pins the busy state's words
 * instead: the heading, the attention panel, and the three count tiles. The employer-word ban is in
 * board-hire-home.spec.ts. Run: E2E_REUSE_SERVER=1 npx playwright test e2e/assess/board-hire.spec.ts.
 */
test("Hire overview keeps the HireHome board's words", async ({ page, context }) => {
  test.setTimeout(300_000);
  const org = await seedHireOrg();
  await signedInAs(context, org.account);
  await openPage(page, `/app/${org.slug}/dashboard`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Overview");
  await expect(page.getByText("Acme Health Trust").first()).toBeVisible();
  // The attention panel waits on the results read, which the cold dev server answers well after the h1 paints.
  await expect(page.getByText("Needs you", { exact: true })).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText("4 candidates need a hiring decision")).toBeVisible();
  const glance = page.getByRole("region", { name: "At a glance" });
  for (const tile of ["Candidates", "Assessors", "Upcoming assessments"]) {
    await expect(glance.getByRole("link", { name: new RegExp(`^${tile}`) })).toBeVisible();
  }
  await expect(page.getByText("Band 6 nurse assessment day").first()).toBeVisible();
});
