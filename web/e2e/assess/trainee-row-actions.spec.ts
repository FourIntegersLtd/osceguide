import { expect, test } from "@playwright/test";
import { openPage, signedInAs } from "../support/session";
import { addTrainees, BOARD_FIVE, haveSignedIn, seedPeopleOrg, type PeopleOrg } from "../support/seed-people";

/**
 * The Trainees table offers each row's actions as one line of icon buttons, each reachable by its accessible
 * name; Delete still opens its confirm. Run: E2E_REUSE_SERVER=1 npx playwright test e2e/assess/trainee-row-actions.spec.ts.
 */
let org: PeopleOrg;

test.beforeAll(async () => {
  test.setTimeout(300_000);
  org = await seedPeopleOrg();
  await addTrainees(org, [BOARD_FIVE[0]!].map((p) => ({ ...p, cohort: null })));
  haveSignedIn([BOARD_FIVE[0]!.email]);
});

test("trainee row actions sit in one menu, each reachable by name, and Delete still confirms", async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await signedInAs(context, org.account);
  const page = await context.newPage();
  await openPage(page, `/app/${org.slug}/trainees`);
  const row = page.locator('[data-testid="trainee-row"]').first();
  await row.waitFor();
  // One trigger per row, not a line of icon buttons.
  const trigger = row.getByRole("button", { name: /^Actions for / });
  await expect(trigger).toBeVisible();
  for (const name of ["Edit", "Delete", "Anonymise"]) await expect(row.getByRole("button", { name, exact: true })).toHaveCount(0);
  await trigger.click();
  for (const name of ["Edit", "Revoke", "Anonymise", "Delete"]) {
    await expect(page.getByRole("menuitem", { name: new RegExp(`^${name}`) })).toBeVisible();
  }
  await page.screenshot({ path: ".verify/trainee-row-actions-menu.png" });
  await page.getByRole("menuitem", { name: /^Delete/ }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.screenshot({ path: ".verify/trainee-row-actions-after.png" });
});
