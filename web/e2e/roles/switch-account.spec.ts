import { expect, test } from "@playwright/test";
import { call, login, PASSWORD, register, stamp } from "../support/api";
import { expectMenu } from "../support/menu";
import { openPage, signedInAs, signInOnThisPage } from "../support/session";
import { needRole, world } from "../support/world";

// One browser tab, more than one person: what the last one did must not decide where the next lands.

test("SWITCH-1 a learner signs out and an institution admin signs in on the same tab", async ({ page, context }) => {
  needRole("consumer", "admin");
  await signedInAs(context, "consumer");
  await openPage(page, "/app/me/dashboard"); // remembers "me" as the last workspace
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await signInOnThisPage(page, world().accounts.admin);
  await expect(page).toHaveURL(new RegExp(`/app/${world().slug}(/|$)`), { timeout: 60_000 });
});

test("SWITCH-2 after a session ends, only the same person is taken back to the page", async ({ page, context }) => {
  needRole("admin", "consumer");
  const { slug, accounts } = world();
  const where = `/app/${slug}/sittings`;
  await signedInAs(context, "admin");
  await openPage(page, where);

  // The session ends (the cookies go); the reload is sent to sign in, with a way back.
  await context.clearCookies();
  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(page).toHaveURL(/\/login\?next=/);
  await signInOnThisPage(page, accounts.admin);
  await expect(page).toHaveURL(new RegExp(`${where}$`), { timeout: 60_000 });

  // Ended again, and somebody else signs in on that form: their own landing, not the admin's page.
  await context.clearCookies();
  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(page).toHaveURL(/\/login\?next=/);
  await signInOnThisPage(page, accounts.consumer);
  await expect(page).toHaveURL(/\/app\/me(\/|$)/, { timeout: 60_000 });
  await expectMenu(page, { shows: [], hides: ["Sittings"] });
});

test("SWITCH-3 deleting your account ends on the sign-in page that says so", async ({ page, context }) => {
  // A throwaway account of its own: closing it must not touch the shared world.
  const email = `e2e-close-${stamp()}@example.com`;
  await register(email, "Cora Closer");
  await call(await login(email, PASSWORD), "/api/v1/me", { method: "PATCH", body: { exam_code: "sca" } });
  await signedInAs(context, { email, password: PASSWORD });
  await openPage(page, "/app/me/settings");
  await page.getByRole("button", { name: "Delete account" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("textbox").first().fill("DELETE");
  await dialog.getByLabel(/^Password/).fill(PASSWORD);
  await dialog.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Delete my account" }).click();
  await expect(page).toHaveURL(/\/login\?deleted=1$/, { timeout: 60_000 });
  await expect(page.getByText("Your account has been deleted")).toBeVisible();
});
