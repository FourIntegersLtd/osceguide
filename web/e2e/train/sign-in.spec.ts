import { expect, test } from "@playwright/test";
import { signIn } from "../../.claude/skills/verify/harness.mjs";
import { dismissOverlays } from "../support/session";
import { needRole, world } from "../support/world";

// TRAIN-1: a learner signs in through the real form, keeps the session across
// a reload, and signs out. Sign-in is the verify harness's own `signIn`.
test("TRAIN-1 sign in, reload, sign out @staging", async ({ page }, testInfo) => {
  needRole("consumer");
  const learner = world().accounts.consumer;

  // A signed-out visit to a workspace page is sent to the login form, with a way back.
  await page.goto("/app/me/dashboard");
  await expect(page).toHaveURL(/\/login\?next=%2Fapp%2Fme%2Fdashboard/);

  await signIn({ page, dir: testInfo.outputDir, steps: [], problems: [] }, { email: learner.email, password: learner.password });
  await expect(page).toHaveURL(/\/app\//);

  await page.goto("/app/me/dashboard");
  await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
  expect(page.url()).toContain("/app/me/dashboard"); // the reload did not sign us out

  await dismissOverlays(page);
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login/);
  await page.goto("/app/me/dashboard");
  await expect(page).toHaveURL(/\/login\?next=/);
});
