import { expect, test } from "@playwright/test";
import { dismissOverlays, openPage, signedInAs } from "../support/session";

// Help is on every learner screen, and stays once the dock has loaded. It used to be
// gated to study-material routes: the floating button showed, then vanished when the
// dock loaded. On a phone it is the only Help button (the toolbar starts at md), so the
// check runs at phone width, where the old gate left nothing at all.
test.use({ viewport: { width: 390, height: 800 } });

test("TRAIN-7 the Help button stays on every learner screen after the dock loads", async ({ page, context }) => {
  await signedInAs(context, "consumer");
  await openPage(page, "/app/me/dashboard");
  const help = page.getByRole("button", { name: "Help", exact: true });
  await expect(help).toBeVisible({ timeout: 60_000 });

  // Loading the dock is what used to hide the button: open Athena, close her, look again.
  await help.click();
  await page.getByRole("button", { name: /Close/ }).first().click();
  await expect(help).toBeVisible();

  for (const route of ["mocks", "notifications", "discussion", "marketplace"]) {
    await page.goto(`/app/me/${route}`, { waitUntil: "domcontentloaded" });
    await dismissOverlays(page);
    await expect(help, `/${route}`).toBeVisible({ timeout: 60_000 });
  }
});

test("TRAIN-7 the toolbar carries Help on a wide screen, and a Notifications bell", async ({ page, context }) => {
  await page.setViewportSize({ width: 1400, height: 900 });
  await signedInAs(context, "consumer");
  await openPage(page, "/app/me/dashboard");
  await expect(page.getByRole("button", { name: "Help", exact: true })).toBeVisible({ timeout: 60_000 });
  await expect(page.getByRole("link", { name: /^Notifications/ })).toHaveCount(2); // the sidebar item and the toolbar bell
});
