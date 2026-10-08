import { expect, test } from "@playwright/test";
import { openPage, signedInAs } from "../support/session";

// TRAIN-5: the learner changes their name (and it sticks), and sees the plans
// they can buy. Checkout itself is Stripe's page and is not driven.
test("TRAIN-5 update the profile and see the plans", async ({ page, context }) => {
  await signedInAs(context, "consumer");
  await openPage(page, "/app/me/settings");

  const username = page.getByRole("textbox", { name: "Username" });
  await username.fill("Lena Renamed");
  await page.getByRole("button", { name: "Update profile" }).click();
  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(page.getByRole("textbox", { name: "Username" })).toHaveValue("Lena Renamed");

  await page.getByRole("tab", { name: "Payments" }).click();
  await expect(page.getByRole("radiogroup", { name: "Plan" })).toBeVisible();
  await expect(page.getByRole("button", { name: /^Upgrade now/ })).toBeVisible();
  // The terms box gates the payment.
  await expect(page.getByRole("checkbox", { name: /Terms of Service/ })).not.toBeChecked();
});
