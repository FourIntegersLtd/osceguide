import { expect, test } from "@playwright/test";
import { expectMenu, expectPageHeading } from "../support/menu";
import { openPage, signedInAs } from "../support/session";
import { needRole, world } from "../support/world";
import { PASSWORD } from "../support/api";
import { psql } from "../support/db";
import { decide } from "../support/seed-results";
import { seedHireOrg } from "../support/seed-hire";

// HIRE-1: the employer workspace is the Assess screens in employer wording.
test("HIRE-1 an employer admin sees the hiring menu, not the institution's @staging", async ({ page, context }) => {
  needRole("hireAdmin");
  const w = world();
  await signedInAs(context, "hireAdmin");
  await openPage(page, `/app/${w.hireSlug}/dashboard`);
  // Employer wording: the institution's "Sittings" and "People" are not offered.
  await expectMenu(page, { shows: ["Overview", "Assessments", "Results", "Now running", "Candidates", "Exams"], hides: ["Sittings", "People", "Build"] });

  await openPage(page, `/app/${w.hireSlug}/sittings`);
  await expectPageHeading(page);
  await expect(page.getByRole("heading", { name: "Assessments", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Sittings", exact: true })).toHaveCount(0);
  await expect(page.getByText(/not authorised|permission|forbidden/i)).toHaveCount(0);

  await openPage(page, `/app/${w.hireSlug}/trainees`);
  await expect(page.getByRole("heading", { name: "Candidates", exact: true })).toBeVisible();
});

test("HIRE-2 a candidate is shown only My assessments @staging", async ({ page, context }) => {
  needRole("hireCandidate");
  const w = world();
  await signedInAs(context, "hireCandidate");
  await openPage(page, `/app/${w.hireSlug}/trainee`);
  await expectMenu(page, { shows: ["My assessments"], hides: ["Assessments", "Candidates", "Overview", "Now running"] });
});

// HIRE-3: the admin opens the finished assessment and its decisions page shows the hiring tiles and decision pills.
test("HIRE-3 an admin reaches the decisions page with Hired tiles and hiring decision pills @staging", async ({ page, context }) => {
  test.setTimeout(300_000);
  const org = await seedHireOrg();
  const done = psql(`SELECT id FROM sittings WHERE name = 'Band 5 recruitment day' AND org_id = (SELECT id FROM organizations WHERE slug = '${org.slug}');`).trim();
  await decide(org, done, 3, "pass", "signed");
  await signedInAs(context, org.account);

  await openPage(page, `/app/${org.slug}/sittings`);
  // A finished assessment waits under its own tab, not with the upcoming ones.
  await page.getByRole("tab", { name: /^Waiting for decisions/ }).click();
  await page.getByRole("link", { name: /Band 5 recruitment day/ }).first().click();
  await expect(page.getByRole("heading", { name: "Band 5 recruitment day" }).first()).toBeVisible();

  await openPage(page, `/app/${org.slug}/sittings/${done}/results`);
  const tiles = page.getByRole("group", { name: "Hiring decisions" });
  for (const label of ["Hired", "Reserve list", "Not hired", "Still to decide"]) await expect(tiles).toContainText(label);
  await expect(page.getByText("Hiring decision", { exact: true }).first()).toBeVisible();
  await page.getByRole("button", { name: /^Open / }).first().click();
  await expect(page.getByText("2. Hiring decision")).toBeVisible();
  await expect(page.getByText("Only your team sees this. Candidates never do.")).toBeVisible();
  await expect(page.locator("#recruitment-outcome")).toContainText("Reserve list");
});

// HIRE-4: the employer's candidate reads My assessments, the assessment and a released result in employer words,
// is never offered practice, and never sees the hiring decision (docs/institution-overhaul/hire/boards/HireCandidate*).
test("HIRE-4 a candidate sees their assessments and result, no practice and no hiring decision @staging", async ({ page, context }) => {
  test.setTimeout(300_000);
  const org = await seedHireOrg();
  const done = psql(`SELECT id FROM sittings WHERE name = 'Band 5 recruitment day' AND org_id = (SELECT id FROM organizations WHERE slug = '${org.slug}');`).trim();
  await decide(org, done, 3, "pass", "released");
  const candidate = org.people[3];
  if (!candidate) throw new Error("seed-hire has no fourth candidate");
  await signedInAs(context, { email: candidate.email, password: PASSWORD });

  await openPage(page, `/app/${org.slug}/trainee`);
  await expect(page.getByRole("heading", { name: "My assessments", exact: true })).toBeVisible();
  await expect(page.getByText("Past assessments")).toBeVisible();
  await expect(page.getByText(/keep practising|self practice|practice sessions|practise/i)).toHaveCount(0);

  await page.getByRole("link", { name: /Band 5 recruitment day/ }).click();
  await expect(page.getByRole("heading", { name: "Band 5 recruitment day" })).toBeVisible();
  await expect(page.getByText(/keep practising|self practice|practise/i)).toHaveCount(0);

  await page.getByRole("link", { name: "Read your result" }).click();
  await expect(page.getByRole("heading", { name: /^Pass · \d+ of \d+ stations$/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "I have read this" })).toBeVisible();
  const body = page.locator("body");
  await expect(body).not.toContainText(/keep practising|self practice/i);
  await expect(body).not.toContainText(/recruitment outcome|hiring decision|\bhired\b|not hired|\bhold\b/i);
});

// HIRE-5: practice and mock exams are not part of an employer's account: the page says so and links home.
test("HIRE-5 an employer admin opening mocks gets the refusal page with a way back @staging", async ({ page, context }) => {
  needRole("hireAdmin");
  const w = world();
  await signedInAs(context, "hireAdmin");
  await openPage(page, `/app/${w.hireSlug}/mocks`);
  await expect(page.getByRole("heading", { name: "This is not part of your employer's account" })).toBeVisible();
  await expect(page.getByRole("link", { name: /^Go to / })).toHaveAttribute("href", `/app/${w.hireSlug}/dashboard`);
});

// HIRE-6: a training assessment keeps feedback only: its results page says so and offers no hiring decision.
test("HIRE-6 a training assessment's results show the notice and no hiring decision @staging", async ({ page, context }) => {
  test.setTimeout(300_000);
  const org = await seedHireOrg({ training: true });
  const id = psql(`SELECT id FROM sittings WHERE name = 'Band 5 training rotation' AND org_id = (SELECT id FROM organizations WHERE slug = '${org.slug}');`).trim();
  await signedInAs(context, org.account);
  await openPage(page, `/app/${org.slug}/sittings/${id}/results`);
  await expect(page.getByText(/This was a training assessment/i)).toBeVisible();
  await expect(page.getByText("Hiring decision", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("group", { name: "Hiring decisions" })).toHaveCount(0);
});
