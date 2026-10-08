import { expect, test } from "@playwright/test";
import { call } from "../support/api";
import { adminToken } from "../support/sitting";
import { openPage, signedInAs } from "../support/session";
import { world } from "../support/world";

// ASSESS-1: an institution admin schedules an exam sitting through the console.
test("ASSESS-1 admin schedules a sitting and finds it listed", async ({ page, context }) => {
  const w = world();
  await signedInAs(context, "admin");

  await openPage(page, `/app/${w.slug}/dashboard`);
  // Setup is done by global-setup, so the guide points at the one step left.
  await expect(page.getByText("Everything is in place. Schedule the first sitting.")).toBeVisible();
  await page.getByRole("link", { name: "Schedule a sitting" }).first().click();

  await expect(page.getByRole("heading", { level: 1, name: "Schedule a sitting" })).toBeVisible();
  const name = `Journey sitting ${Date.now().toString(36)}`;
  const create = page.getByRole("button", { name: "Create sitting" });
  await expect(create).toBeDisabled(); // nothing to create until it has a name
  await page.getByRole("textbox", { name: "Name" }).fill(name);
  await page.getByRole("button", { name: /^Exam/ }).click();
  await page.getByLabel("Scheduled for").fill("2030-03-04T10:00");
  await create.click();

  // Lands on the new sitting, with the guide asking for the circuit.
  await expect(page.getByRole("heading", { level: 1, name })).toBeVisible();
  await expect(page.getByText("Scheduled", { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("list", { name: "Steps" })).toContainText("Circuits");
  await expect(page.getByRole("link", { name: "Add a circuit" }).first()).toBeVisible();

  // It is on the list, and the api agrees on what was scheduled.
  await openPage(page, `/app/${w.slug}/sittings`);
  await expect(page.getByRole("link", { name: new RegExp(name) })).toBeVisible();
  const listed = await call(await adminToken(), `/api/v1/orgs/${w.slug}/sittings?limit=50`);
  const row = (listed.items as { name: string; mode: string; status: string }[]).find((item) => item.name === name);
  expect(row).toMatchObject({ mode: "exam", status: "scheduled" });
});
