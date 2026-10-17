import { expect, test } from "@playwright/test";
import { expectMenu, expectPageHeading } from "../support/menu";
import { signIn } from "../../.claude/skills/verify/harness.mjs";
import { openPage, signedInAs, signInOnThisPage } from "../support/session";
import { needRole, world } from "../support/world";

// CONSOLE-1: a platform admin runs the staff console; nobody else gets in.
test("CONSOLE-1 a platform admin opens the console and finds the organisations @staging", async ({ page, context }) => {
  needRole("platform");
  await signedInAs(context, "platform");
  await openPage(page, "/staff");
  await expectMenu(page, { shows: ["Overview", "Organisations", "Users", "Audit log"] });
  await openPage(page, "/staff/organizations");
  await expectPageHeading(page);
  await openPage(page, "/staff/users");
  await expectPageHeading(page);
});

const STAFF_MENU = ["Organisations", "Users", "Audit log"];

// CONSOLE-2: someone without the console who opens it is sent to their own workspace; the staff
// menu never renders (it used to wrap a "You do not have access to this" body).
test("CONSOLE-2 a learner who opens the console lands in their own workspace @staging", async ({ page, context }) => {
  needRole("consumer");
  await signedInAs(context, "consumer");
  await page.goto("/staff/organizations", { waitUntil: "domcontentloaded" });
  await expect(page).toHaveURL(/\/app\/me(\/|$)/, { timeout: 60_000 });
  await expectMenu(page, { shows: [], hides: STAFF_MENU });
  await expect(page.getByText("You do not have access to this")).toHaveCount(0);
});

test("CONSOLE-3 an institution admin who opens the console lands in their institution @staging", async ({ page, context }) => {
  needRole("admin");
  await signedInAs(context, "admin");
  await page.goto("/staff", { waitUntil: "domcontentloaded" });
  await expect(page).toHaveURL(new RegExp(`/app/${world().slug}(/|$)`), { timeout: 60_000 });
  await expectMenu(page, { shows: [], hides: STAFF_MENU });
});

// CONSOLE-4: two people, one tab. A platform admin signed out of /staff/users and an institution
// admin signed in on the same form: `/login?next=/staff/users` sent them to the staff console.
test("CONSOLE-4 signing out of the console does not send the next person there @staging", async ({ page }, testInfo) => {
  needRole("platform", "admin");
  const run = { page, dir: testInfo.outputDir, steps: [], problems: [] };
  await signIn(run, { email: world().accounts.platform.email, password: world().accounts.platform.password });
  await openPage(page, "/staff/users");
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login$/);

  // The next person signs in on the form the sign-out left, not a fresh /login.
  await signInOnThisPage(page, world().accounts.admin);
  await expect(page).toHaveURL(new RegExp(`/app/${world().slug}(/|$)`), { timeout: 60_000 });
  await expectMenu(page, { shows: [], hides: STAFF_MENU });
});
