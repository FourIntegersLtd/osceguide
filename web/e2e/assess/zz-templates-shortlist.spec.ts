/**
 * Exam templates and the CSV shortlist, in an employer workspace (hire words).
 * Named to sort after build-sitting.spec.ts; it makes its own org and creates no sitting.
 * Screenshots go to TEMPLATE_SHOTS when set.
 */
import { readFileSync } from "node:fs";
import { expect, test, type Browser, type Page } from "@playwright/test";
import { psql } from "../support/db";
import { seedHireOrg } from "../support/seed-hire";
import type { SittingsOrg } from "../support/seed-sittings";
import { openPage, signedInAs } from "../support/session";

const SHOTS = process.env.TEMPLATE_SHOTS ?? "";
const VIEWPORTS = [
  { name: "1440", width: 1440, height: 1000 },
  { name: "390", width: 390, height: 900 },
] as const;

let hire: SittingsOrg;
test.beforeAll(async () => {
  test.setTimeout(300_000);
  hire = await seedHireOrg();
});

async function pageFor(browser: Browser, viewport: { width: number; height: number }): Promise<Page> {
  const context = await browser.newContext({ viewport });
  await signedInAs(context, hire.account);
  await context.addInitScript(() => localStorage.setItem("installPromptDismissed", "true"));
  return context.newPage();
}

const shot = async (page: Page, name: string) => {
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: true });
};

for (const viewport of VIEWPORTS) {
  test(`a setup is saved as a template, started from, renamed and deleted, ${viewport.name}`, async ({ browser }) => {
    const label = `Nurse day ${viewport.name}`;
    const page = await pageFor(browser, viewport);
    await openPage(page, `/app/${hire.slug}/sittings/new`);
    await expect(page.getByTestId("template-picker")).toHaveCount(0);
    await page.getByRole("radio", { name: /^Formal exam/ }).click();
    await page.getByRole("textbox", { name: "Name" }).fill("Template source");
    await page.getByRole("button", { name: "Continue" }).click();
    await page.getByRole("button", { name: "Add from this exam" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.locator("li, tr, article, div").filter({ hasText: "Chest pain history" }).getByRole("button", { name: "Add", exact: true }).last().click();
    await dialog.getByRole("button", { name: "Done" }).click();
    await page.getByRole("button", { name: "Continue" }).click();
    const rows = page.getByRole("listitem").filter({ has: page.getByRole("checkbox") });
    await rows.nth(0).locator("label").click();
    await rows.nth(1).locator("label").click();
    await page.getByRole("button", { name: "Continue" }).click();
    await page.getByRole("button", { name: "Continue" }).click();
    await page.getByRole("radio", { name: /per candidate/i }).click();
    await page.getByRole("button", { name: "Continue" }).click();
    const save = page.getByTestId("save-template");
    await expect(save).toContainText("Save this setup as a template");
    await save.getByRole("textbox").fill(label);
    await save.getByRole("button", { name: "Save template" }).click();
    await expect(save.getByText(`Saved as "${label}"`)).toBeVisible();
    await shot(page, `save-${viewport.name}`);

    await openPage(page, `/app/${hire.slug}/sittings/new`);
    const picker = page.getByTestId("template-picker");
    await picker.getByLabel(/template$/).selectOption({ label });
    await picker.getByRole("button", { name: "Use this template" }).click();
    await expect(page.getByRole("radio", { name: /^Formal exam/ })).toBeChecked();
    await shot(page, `picker-${viewport.name}`);
    // A template carries no name or date: those are still the new schedule's own.
    await page.getByRole("textbox", { name: "Name" }).fill("From the template");
    await page.locator("#sitting-date").fill("2030-03-04");
    await page.getByRole("button", { name: "Continue" }).click();
    await expect(page.getByText("Chest pain history").first()).toBeVisible();

    await openPage(page, `/app/${hire.slug}/sittings/new`);
    await picker.getByLabel(/template$/).selectOption({ label });
    await picker.getByRole("button", { name: "Rename" }).click();
    await picker.getByRole("textbox", { name: "Template name" }).fill(`${label} v2`);
    await picker.getByRole("button", { name: "Save name" }).click();
    await expect(picker.getByRole("option", { name: `${label} v2` })).toHaveCount(1);
    await picker.getByLabel(/template$/).selectOption({ label: `${label} v2` });
    await picker.getByRole("button", { name: "Delete" }).click();
    await expect(picker.getByRole("option", { name: `${label} v2` })).toHaveCount(0);
  });

  test(`the shortlist downloads as a BOM CSV of decided candidates only, ${viewport.name}`, async ({ browser }) => {
    const sittingId = psql(`SELECT s.id FROM sittings s WHERE s.name = 'Band 5 recruitment day' AND s.org_id = (SELECT id FROM organizations WHERE slug = '${hire.slug}');`).trim();
    const page = await pageFor(browser, viewport);
    await openPage(page, `/app/${hire.slug}/sittings/${sittingId}/results`);
    await shot(page, `results-${viewport.name}`);
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: "Download shortlist" }).click(),
    ]);
    expect(download.suggestedFilename()).toMatch(/-shortlist\.csv$/);
    const text = readFileSync(await download.path(), "utf8");
    expect(text.startsWith("﻿rank,name,email,score,outcome,reason\n")).toBe(true);
    // Every candidate here is still to decide, so nothing is shortlisted: only the header remains.
    expect(text.trim().split("\n").slice(1)).toEqual([]);
  });
}
