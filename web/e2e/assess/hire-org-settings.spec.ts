import { test, expect } from "@playwright/test";
import { openPage, signedInAs } from "../support/session";
import { seedHireOrg } from "../support/seed-hire";

/** Hire Settings, Organisation tab: the contact email is editable and saves with the name (HireSettings board). */
test("an employer admin edits and clears the contact email", async ({ page, context }) => {
  test.setTimeout(300_000);
  const org = await seedHireOrg();
  await signedInAs(context, org.account);
  await openPage(page, `/app/${org.slug}/settings`);
  await page.getByRole("tab", { name: "Organisation" }).click();

  const contact = page.getByLabel("Contact email");
  const save = page.getByRole("button", { name: "Save changes" });
  await expect(contact).toBeEditable();
  await expect(save).toBeDisabled();

  await contact.fill("not an email");
  await expect(save).toBeDisabled();

  // Looks like an email, so Save is offered; the server refuses a reserved domain and its refusal is shown.
  await contact.fill("people@acme.test");
  await expect(save).toBeEnabled();
  await save.click();
  await expect(page.getByText("That contact email does not look right")).toBeVisible();
  await expect(save).toBeEnabled();

  await contact.fill("people@acme-health.co.uk");
  await expect(save).toBeEnabled();
  await save.click();
  await expect(save).toBeDisabled();
  await page.reload();
  await page.getByRole("tab", { name: "Organisation" }).click();
  await expect(page.getByLabel("Contact email")).toHaveValue("people@acme-health.co.uk");

  await page.getByLabel("Contact email").fill("");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByRole("button", { name: "Save changes" })).toBeDisabled();
  await page.reload();
  await page.getByRole("tab", { name: "Organisation" }).click();
  await expect(page.getByLabel("Contact email")).toHaveValue("");
});
