import { expect, test } from "@playwright/test";
import { PASSWORD, stamp } from "../support/api";
import { dismissOverlays, signedInAs } from "../support/session";
import { world } from "../support/world";

// TRAIN-2: someone new creates an account through the form, is asked which
// exam they are sitting, and lands on a dashboard that points at their first station.
test("TRAIN-2 register, choose an exam, reach the first-station prompt", async ({ page }) => {
  const email = `e2e-reg-${stamp()}@example.com`;
  await page.goto("/register", { waitUntil: "networkidle" });
  await page.waitForTimeout(1500); // hydrate before submitting: a server-rendered submit is a GET (A-3)
  await dismissOverlays(page);
  await page.getByLabel("Name").fill("Rhea Registers");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByLabel("Confirm password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page.getByText("Which exam are you sitting?")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByRole("button", { name: "Continue" })).toBeDisabled();
  await page.getByRole("radio", { name: /^SCA/ }).click();
  await page.getByRole("button", { name: "Continue" }).click();

  await dismissOverlays(page); // Athena's walkthrough is a voice feature; closing it is part of the journey
  await expect(page.getByRole("heading", { level: 1, name: "Where you stand" })).toBeVisible({ timeout: 60_000 });
  await expect(page.getByRole("link", { name: "Start your first station" })).toBeVisible();
});

// An account that has not chosen an exam is held at the picker on every personal page.
test("TRAIN-2b the picker holds until an exam is chosen", async ({ page, context }) => {
  await signedInAs(context, "newcomer");
  await page.goto("/app/me/dashboard");
  await expect(page.getByText("Which exam are you sitting?")).toBeVisible({ timeout: 60_000 });
  await page.goto("/app/me/mocks");
  await expect(page.getByText("Which exam are you sitting?")).toBeVisible();
  expect(world().accounts.newcomer.email).toContain("newcomer");
});
