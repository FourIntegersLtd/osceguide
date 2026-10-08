import { expect, test } from "@playwright/test";
import { expectMenu, expectPageHeading } from "../support/menu";
import { openPage, signedInAs } from "../support/session";
import { needRole, world } from "../support/world";

// HIRE-1: the employer workspace is the Assess screens in employer wording.
test("HIRE-1 an employer admin sees the hiring menu, not the institution's @staging", async ({ page, context }) => {
  needRole("hireAdmin");
  const w = world();
  await signedInAs(context, "hireAdmin");
  await openPage(page, `/app/${w.hireSlug}/dashboard`);
  // Employer wording: the institution's "Sittings" and "People" are not offered.
  await expectMenu(page, { shows: ["Overview", "Assessments", "Now running", "Candidates", "Build"], hides: ["Sittings", "People"] });

  await openPage(page, `/app/${w.hireSlug}/sittings`);
  await expectPageHeading(page);
  await expect(page.getByText(/not authorised|permission|forbidden/i)).toHaveCount(0);
});

test("HIRE-2 a candidate is shown only My assessments @staging", async ({ page, context }) => {
  needRole("hireCandidate");
  const w = world();
  await signedInAs(context, "hireCandidate");
  await openPage(page, `/app/${w.hireSlug}/trainee`);
  await expectMenu(page, { shows: ["My assessments"], hides: ["Assessments", "Candidates", "Overview", "Now running"] });
});
