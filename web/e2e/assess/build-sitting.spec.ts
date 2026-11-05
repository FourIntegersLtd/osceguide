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
  // Six steps unlock in order: Continue stays shut until the step is answered.
  const next = page.getByRole("button", { name: "Continue" });
  await expect(next).toBeDisabled();
  await page.getByRole("textbox", { name: "Name" }).fill(name);
  await page.getByRole("button", { name: /^Formal exam/ }).click();
  await page.getByLabel("Date").fill("2030-03-04");
  await next.click();

  await expect(page.getByRole("heading", { name: "Pick the stations" })).toBeVisible();
  await expect(next).toBeDisabled();
  await page.getByRole("button", { name: "Add", exact: true }).first().click();
  await next.click();

  await expect(page.getByRole("heading", { name: "Who is sitting it?" })).toBeVisible();
  await page.getByRole("button", { name: "Pick", exact: true }).first().click();
  await next.click();
  await next.click(); // timing keeps the exam's defaults
  await next.click(); // the supervisor is optional

  await expect(page.getByRole("heading", { name: "Review and create" })).toBeVisible();
  await page.getByRole("button", { name: "Create sitting" }).click();

  // Lands on the new sitting, with the circuit the wizard made.
  await expect(page.getByRole("heading", { level: 1, name })).toBeVisible();
  await expect(page.getByText("Scheduled", { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("list", { name: "Steps" })).toContainText("Circuits");

  // It is on the list, and the api agrees on what was scheduled.
  await openPage(page, `/app/${w.slug}/sittings`);
  await expect(page.getByRole("link", { name: new RegExp(name) })).toBeVisible();
  const listed = await call(await adminToken(), `/api/v1/orgs/${w.slug}/sittings?limit=50`);
  const row = (listed.items as { id: string; name: string; mode: string; status: string }[]).find((item) => item.name === name);
  expect(row).toMatchObject({ mode: "exam", status: "scheduled" });

  // The circuit the wizard promised exists: the list read carries none, the sitting read does.
  const sitting = await call(await adminToken(), `/api/v1/orgs/${w.slug}/sittings/${row?.id}`);
  expect((sitting.circuits as unknown[]).length).toBeGreaterThan(0);
});
