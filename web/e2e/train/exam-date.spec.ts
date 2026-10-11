import { expect, test } from "@playwright/test";
import { openPage, signedInAs } from "../support/session";

// TRAIN-5: the exam date is set from a calendar on the dashboard header. Picking a day saves it
// and the popover closes by itself; it used to stay open with no sign that anything had happened.
test("TRAIN-5 picking an exam day saves it and closes the calendar", async ({ page, context }) => {
  await signedInAs(context, "consumer");
  await openPage(page, "/app/me/dashboard");

  // Start from "no date": clear one left by an earlier run.
  const edit = page.getByRole("button", { name: /^Edit .*date/i });
  if (await edit.isVisible()) {
    await edit.click();
    await page.getByRole("button", { name: "Clear date" }).click();
  }
  await page.getByRole("button", { name: /^Add .*date/i }).click();

  const calendar = page.getByRole("dialog");
  await calendar.getByRole("button", { name: /\b28th\b/ }).first().click();
  await expect(calendar).toBeHidden();
  await expect(page.getByText(/^Exam: 28 /)).toBeVisible();
  await expect(page.getByText(/^\d+ (week|day)s? to go$/)).toBeVisible();

  await page.getByRole("button", { name: /^Edit .*date/i }).click();
  await page.getByRole("button", { name: "Clear date" }).click();
  await expect(page.getByRole("button", { name: /^Add .*date/i })).toBeVisible();
});
