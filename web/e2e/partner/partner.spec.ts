import { expect, test } from "@playwright/test";
import { expectMenu, expectPageHeading } from "../support/menu";
import { openPage, signedInAs } from "../support/session";
import { needRole, world } from "../support/world";

// PARTNER-1: a partner admin watches the audience they sent us and manages their editors.
test("PARTNER-1 a partner admin opens Overview, Reporting and Team @staging", async ({ page, context }) => {
  needRole("partnerAdmin");
  const w = world();
  await signedInAs(context, "partnerAdmin");
  await openPage(page, `/app/${w.partnerSlug}/dashboard`);
  // A partner never examines: no sittings or people menu.
  await expectMenu(page, { shows: ["Overview", "Reporting", "Team"], hides: ["Sittings", "People", "Now running"] });

  await openPage(page, `/app/${w.partnerSlug}/reporting`);
  await expectPageHeading(page, /reporting/i);
  await openPage(page, `/app/${w.partnerSlug}/team`);
  await expectPageHeading(page);
  await expect(page.getByText(w.accounts.partnerAdmin.email).first()).toBeVisible();
});
