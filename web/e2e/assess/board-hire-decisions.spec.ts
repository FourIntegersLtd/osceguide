import { test, expect } from "@playwright/test";
import { openPage, signedInAs } from "../support/session";
import { psql } from "../support/db";
import { decide } from "../support/seed-results";
import { seedHireOrg } from "../support/seed-hire";

/**
 * HireDecisions (the hire board for /sittings/[id]/results). The board file is not on disk, so this spec asserts the
 * board's words and states rather than diffing pixels: the Hired / Reserve list / Not hired / Still to decide tiles,
 * the Hiring decision column, and the "1. Result" / "2. Hiring decision" pills with the team-only note.
 * Run: E2E_REUSE_SERVER=1 npx playwright test e2e/assess/board-hire-decisions.spec.ts.
 */
test("Hire decisions shows the hiring tiles, column and pills", async ({ page, context }) => {
  test.setTimeout(300_000);
  const org = await seedHireOrg();
  const done = psql(`SELECT id FROM sittings WHERE name = 'Band 5 recruitment day' AND org_id = (SELECT id FROM organizations WHERE slug = '${org.slug}');`).trim();
  await decide(org, done, 3, "pass", "draft");
  await signedInAs(context, org.account);
  await openPage(page, `/app/${org.slug}/sittings/${done}/results`);

  await expect(page.getByRole("link", { name: "‹ Results" })).toBeVisible();
  const tiles = page.getByRole("group", { name: "Hiring decisions" });
  for (const label of ["Hired", "Reserve list", "Not hired", "Still to decide"]) await expect(tiles).toContainText(label);
  await expect(page.getByText("Hiring decision", { exact: true }).first()).toBeVisible();

  await page.getByRole("button", { name: /^Open / }).first().click();
  await expect(page.getByText("1. Result")).toBeVisible();
  await expect(page.getByText("2. Hiring decision")).toBeVisible();
  await expect(page.getByText("Only your team sees this. Candidates never do.")).toBeVisible();
  for (const pill of ["Hired", "Reserve list", "Not hired", "Withdrawn"]) await expect(page.getByRole("button", { name: pill, exact: true })).toBeVisible();
});
