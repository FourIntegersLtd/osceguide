/**
 * Hire arm, Part 2 of the review plan: the first-assessment checklist, rotations dealt to assessors in the
 * schedule wizard, and the ranked comparison with a required reason for a hire. Boards: HireHome (New account),
 * HireScheduleAssessment, HireDecisions. Screenshots go to HIRE_SHOTS when set.
 * Run: E2E_REUSE_SERVER=1 VERIFY_WEB_URL=http://localhost:3101 npx playwright test e2e/assess/hire-part2.spec.ts
 */
import { expect, test, type Browser, type Page } from "@playwright/test";
import { psql } from "../support/db";
import { seedHireOrg } from "../support/seed-hire";
import { seedSittingsOrg, type SittingsOrg } from "../support/seed-sittings";
import { openPage, signedInAs } from "../support/session";

const SHOTS = process.env.HIRE_SHOTS ?? "";
const VIEWPORTS = [
  { name: "1440", width: 1440, height: 1000 },
  { name: "390", width: 390, height: 900 },
] as const;

let hire: SittingsOrg;
let fresh: SittingsOrg;

test.beforeAll(async () => {
  test.setTimeout(300_000);
  hire = await seedHireOrg();
  fresh = await seedSittingsOrg({ adminName: "Ms Clarke", trainees: 0, supervisors: [], org: { type: "employer", name: "Fresh Trust" } });
});

async function pageFor(browser: Browser, org: SittingsOrg, viewport: { width: number; height: number }): Promise<Page> {
  const context = await browser.newContext({ viewport });
  await signedInAs(context, org.account);
  await context.addInitScript(() => localStorage.setItem("installPromptDismissed", "true"));
  return context.newPage();
}

const shot = async (page: Page, name: string) => {
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: true });
};

for (const viewport of VIEWPORTS) {
  test(`a new employer sees the four-step checklist, ${viewport.name}`, async ({ browser }) => {
    const page = await pageFor(browser, fresh, viewport);
    await openPage(page, `/app/${fresh.slug}/dashboard`);
    await expect(page.getByRole("heading", { level: 1, name: "Welcome. Four steps to your first assessment" })).toBeVisible();
    await expect(page.getByRole("list", { name: "Steps" }).getByRole("listitem")).toHaveCount(4);
    await expect(page.getByText("Next step")).toBeVisible();
    await shot(page, `checklist-${viewport.name}`);
  });

  test(`a running employer has no checklist, ${viewport.name}`, async ({ browser }) => {
    const page = await pageFor(browser, hire, viewport);
    await openPage(page, `/app/${hire.slug}/dashboard`);
    await expect(page.getByRole("heading", { level: 1, name: "Overview" })).toBeVisible();
    await expect(page.getByText("Four steps to your first assessment")).toHaveCount(0);
  });

  test(`the schedule wizard deals candidates to the chosen assessors, ${viewport.name}`, async ({ browser }) => {
    const page = await pageFor(browser, hire, viewport);
    await openPage(page, `/app/${hire.slug}/sittings/new`);
    await page.getByRole("radio", { name: /^Formal exam/ }).click();
    await page.getByRole("textbox", { name: "Name" }).fill("Band 6 nurse, November intake");
    await page.getByRole("button", { name: "Continue" }).click();
    await page.getByRole("button", { name: "Add from this exam" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.locator("li, tr, article, div").filter({ hasText: "Chest pain history" }).getByRole("button", { name: "Add", exact: true }).last().click();
    await dialog.getByRole("button", { name: "Done" }).click();
    await page.getByRole("button", { name: "Continue" }).click();
    // The checkbox is visually hidden behind its label: click the label, as a person does.
    const rows = page.getByRole("listitem").filter({ has: page.getByRole("checkbox") });
    for (let n = 0; n < 5; n += 1) {
      await rows.nth(n).locator("label").click();
      await expect(rows.nth(n).getByRole("checkbox")).toBeChecked();
    }
    await page.getByRole("button", { name: "Continue" }).click();
    await page.getByRole("button", { name: "Continue" }).click();
    // The assessor step: the builder appears once each candidate gets their own assessor.
    await page.getByRole("radio", { name: /per candidate/i }).click();
    await expect(page.getByText("Build the rotations").first()).toBeVisible();
    const pool = page.getByRole("group", { name: "Build the rotations" });
    await pool.getByRole("checkbox").nth(0).check();
    await pool.getByRole("checkbox").nth(1).check();
    await expect(pool.getByRole("status")).toContainText("3");
    await expect(pool.getByRole("status")).toContainText("2");
    // Each candidate's rotation is editable under the proposal.
    await expect(page.getByRole("combobox", { name: /^Assessor for/ })).toHaveCount(5);
    await shot(page, `rotations-${viewport.name}`);
    await page.getByRole("button", { name: "Continue" }).click();
    await expect(page.getByText("with nobody")).toHaveCount(0);
    await shot(page, `rotations-review-${viewport.name}`);
  });

  test(`results rank candidates and a hire needs its reason, ${viewport.name}`, async ({ browser }) => {
    const sittingId = psql(`SELECT s.id FROM sittings s WHERE s.name = 'Band 5 recruitment day' AND s.org_id = (SELECT id FROM organizations WHERE slug = '${hire.slug}');`).trim();
    const page = await pageFor(browser, hire, viewport);
    await openPage(page, `/app/${hire.slug}/sittings/${sittingId}/results`);
    const ranking = page.getByRole("region", { name: "Ranking" });
    await expect(ranking).toBeVisible();
    await expect(ranking.getByRole("button", { name: /^Decide / })).toHaveCount(4);
    await shot(page, `ranking-${viewport.name}`);
    await ranking.getByRole("button", { name: /^Decide / }).first().click();
    await page.locator("#recruitment-outcome").selectOption("hired");
    await expect(page.getByText("Say why you are hiring this candidate.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Save draft" })).toBeDisabled();
    await page.locator("#decision-rationale").fill("Strongest on safety netting and handover.");
    await expect(page.getByText("Say why you are hiring this candidate.")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Save draft" })).toBeEnabled();
    await shot(page, `decision-${viewport.name}`);
  });
}
