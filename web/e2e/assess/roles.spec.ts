import { expect, test } from "@playwright/test";
import { openPage, signedInAs } from "../support/session";
import { world } from "../support/world";

// ASSESS-5: each role sees what it may use and nothing it may not.
test("ASSESS-5 a supervisor can see sittings but not schedule them", async ({ page, context }) => {
  const w = world();
  await signedInAs(context, "supervisor");
  await openPage(page, `/app/${w.slug}/sittings`);
  await expect(page.getByRole("heading", { level: 1, name: "Sittings" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Schedule a sitting" })).toHaveCount(0);
  await openPage(page, `/app/${w.slug}/dashboard`);
  await expect(page.getByRole("link", { name: "Schedule a sitting" })).toHaveCount(0);
});

test("ASSESS-5b a trainee lands on their own portal, not the console", async ({ page, context }) => {
  const w = world();
  await signedInAs(context, "trainee");
  await openPage(page, `/app/${w.slug}/trainee`);
  await expect(page.getByRole("heading", { level: 1, name: /Hello, Tess/ })).toBeVisible();
  await expect(page.getByRole("link", { name: "Schedule a sitting" })).toHaveCount(0);

  // The staff console is not theirs: no sitting controls, whatever the page does instead.
  await page.goto(`/app/${w.slug}/sittings/new`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(3_000);
  await expect(page.getByRole("button", { name: "Continue" })).toHaveCount(0);
});

test("ASSESS-5c the roster lists the trainee, and an admin can add another person", async ({ page, context }) => {
  const w = world();
  await signedInAs(context, "admin");
  await openPage(page, `/app/${w.slug}/trainees`);
  await expect(page.getByRole("row", { name: /Tess Trainee/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "Add people" })).toBeVisible();
});
