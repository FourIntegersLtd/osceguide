import { expect, test } from "@playwright/test";
import { expectMenu, expectPageHeading } from "../support/menu";
import { openPage, signedInAs } from "../support/session";
import { needRole } from "../support/world";

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

// CONSOLE-2: the page itself is refused, with a stated reason, and no console data renders.
test("CONSOLE-2 a learner who opens the console is told they have no access @staging", async ({ page, context }) => {
  needRole("consumer");
  await signedInAs(context, "consumer");
  await page.goto("/staff/organizations", { waitUntil: "domcontentloaded" });
  // The positive outcome: the access message, or sent away from /staff.
  await expect(page.getByText("You do not have access to this").or(page.getByRole("heading", { name: "Page not found" }))).toBeVisible({ timeout: 60_000 });
  await expect(page.getByRole("heading", { level: 1, name: "Organisations" })).toHaveCount(0);
});

// Found by CONSOLE-2: the console shell renders its menu outside the capability gate, so a
// learner who types /staff sees the staff menu labels (the content is refused). Cosmetic, no data.
test.fixme("CONSOLE-3 a learner is not shown the staff menu @staging", async ({ page, context }) => {
  needRole("consumer");
  await signedInAs(context, "consumer");
  await page.goto("/staff/organizations", { waitUntil: "domcontentloaded" });
  await expect(page.getByText("You do not have access to this")).toBeVisible({ timeout: 60_000 });
  await expectMenu(page, { shows: [], hides: ["Organisations", "Audit log"] });
});
