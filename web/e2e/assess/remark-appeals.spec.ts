import { expect, test, type Browser, type Page } from "@playwright/test";
import { call, orgPath, PASSWORD, register, stamp } from "../support/api";
import { seedMarkedSlotAttempt } from "../support/db";
import { openPage, signedInAs } from "../support/session";
import { adminToken, buildSitting, endCircuit, startCircuit, type BuiltSitting } from "../support/sitting";
import { world } from "../support/world";

// ASSESS-12: a released result can be questioned. The candidate asks, a second administrator is
// named and records a new outcome (a new revision, never an edit), a staff-recorded request can be
// declined with a reason, and an administrator can set how long transcripts are kept and delete a
// person's data behind a typed confirmation. Named to run after build-sitting.spec.ts.
test.describe.serial("ASSESS-12 appeals, retention and deleting a person's data", () => {
  let sitting: BuiltSitting;
  let admin: Page;
  let second: Page;
  let trainee: Page;
  const secondEmail = `second-marker-${stamp()}@example.com`;

  test.beforeAll(async ({ browser }) => {
    const w = world();
    sitting = await buildSitting("Appeal run", "exam");
    await startCircuit(sitting);
    await endCircuit(sitting);
    seedMarkedSlotAttempt(sitting.slotId);
    // A second administrator: the second marker cannot be whoever signed off and released.
    await register(secondEmail, "Second Marker");
    await call(await adminToken(), orgPath(w.slug, "/memberships"), { method: "POST", body: { email: secondEmail, role: "institution_admin" } });
    admin = await (await newContext(browser, "admin")).newPage();
    trainee = await (await newContext(browser, "trainee")).newPage();
    const secondContext = await browser.newContext();
    await signedInAs(secondContext, { email: secondEmail, password: PASSWORD });
    second = await secondContext.newPage();
  });

  test.afterAll(async () => {
    for (const page of [admin, second, trainee]) await page.context().close();
  });

  test("the result is marked, signed off and released", async () => {
    const w = world();
    await openPage(admin, `/app/${w.slug}/slots/${sitting.slotId}/review?sitting=${sitting.id}`);
    // Rows re-render as ratings save, so click the first unrated Green until none is left.
    const unrated = admin.locator('button[aria-pressed="false"]', { hasText: /^Green$/ });
    await expect(unrated.first()).toBeVisible({ timeout: 30_000 });
    while ((await unrated.count()) > 0) await unrated.first().click();
    await admin.getByRole("button", { name: "Complete review" }).click();
    await expect(admin.getByText(/Review completed/)).toBeVisible();
    await openPage(admin, `/app/${w.slug}/sittings/${sitting.id}/results`);
    await admin.getByRole("button", { name: "Open Tess Trainee" }).click();
    await admin.getByRole("button", { name: /^Pass/ }).click();
    await admin.getByRole("textbox", { name: /rationale/i }).fill("Journey: met the standard.");
    await admin.getByRole("button", { name: "Sign off" }).click();
    await expect(admin.getByRole("button", { name: "Back to draft" })).toBeVisible();
    await admin.getByRole("button", { name: "Release 1 signed-off result" }).click();
    await admin.getByRole("dialog").getByRole("button", { name: "Release" }).click();
  });

  test("the candidate asks for a review and sees it is with the organisation", async () => {
    const w = world();
    await openPage(trainee, `/app/${w.slug}/trainee/results/${sitting.id}`);
    await trainee.getByRole("button", { name: "Ask for a review" }).click();
    await trainee.getByLabel("Why should this result be looked at again?").fill("I think the communication station was marked too harshly.");
    await trainee.getByRole("button", { name: "Send request" }).click();
    await expect(trainee.getByText(/Your request is with the organisation/)).toBeVisible();
    await expect(trainee.getByText(/marked too harshly/)).toBeVisible();
  });

  test("an administrator names a second marker, who records a new outcome", async () => {
    const w = world();
    await openPage(admin, `/app/${w.slug}/results`);
    await admin.getByRole("tab", { name: "Appeals" }).click();
    await expect(admin.getByText(/marked too harshly/)).toBeVisible();
    await admin.getByRole("button", { name: "Assign second marker" }).click();
    // The person who signed off is not offered.
    await expect(admin.getByRole("option", { name: w.accounts.admin.email })).toHaveCount(0);
    await admin.getByLabel("Second marker", { exact: true }).selectOption({ label: secondEmail });
    await admin.getByRole("button", { name: "Assign", exact: true }).click();
    await expect(admin.getByText("Second marker assigned.")).toBeVisible();

    await openPage(second, `/app/${w.slug}/results`);
    await second.getByRole("tab", { name: "Appeals" }).click();
    await second.getByRole("button", { name: "Record the new outcome" }).click();
    await second.getByRole("button", { name: /^Fail/ }).click();
    await second.getByLabel("Rationale", { exact: true }).fill("Second marker: the communication station fell short.");
    await second.getByRole("button", { name: "Record outcome" }).click();
    await expect(second.getByText(/Recorded as a new revision/)).toBeVisible();
  });

  test("the candidate reads the new outcome and that the review is done", async () => {
    const w = world();
    await openPage(trainee, `/app/${w.slug}/trainee/results/${sitting.id}`);
    await expect(trainee.getByText(/Your result was reviewed/)).toBeVisible();
    await expect(trainee.getByText(/Fail/i).first()).toBeVisible();
  });

  test("a request recorded by staff can be declined with a reason the candidate reads", async () => {
    const w = world();
    await openPage(admin, `/app/${w.slug}/sittings/${sitting.id}/results`);
    await admin.getByRole("button", { name: "Open Tess Trainee" }).click();
    await admin.getByRole("button", { name: "Record a review request" }).click();
    await admin.getByLabel("Reason", { exact: true }).fill("Asked by email after the second marking.");
    await admin.getByRole("button", { name: "Record request" }).click();
    await expect(admin.getByText(/Review request recorded/)).toBeVisible();

    await openPage(admin, `/app/${w.slug}/results`);
    await admin.getByRole("tab", { name: "Appeals" }).click();
    await admin.getByRole("button", { name: "Decline" }).click();
    await admin.getByLabel("Reason", { exact: true }).fill("Two markers have now looked at this and the result stands.");
    await admin.getByRole("button", { name: "Decline request" }).click();
    await expect(admin.getByText(/Declined\. The reason has been sent/)).toBeVisible();

    await openPage(trainee, `/app/${w.slug}/trainee/results/${sitting.id}`);
    await expect(trainee.getByText(/the result stands/i).first()).toBeVisible();
    await expect(trainee.getByText(/Two markers have now looked at this/)).toBeVisible();
  });

  test("an administrator sets how long transcripts are kept", async () => {
    const w = world();
    await openPage(admin, `/app/${w.slug}/settings`);
    await admin.getByRole("tab", { name: "Organisation" }).click();
    await admin.getByLabel("Keep transcripts for").selectOption({ label: "90 days" });
    await admin.getByRole("button", { name: "Save", exact: true }).click();
    await expect(admin.getByText(/Saved\. Transcripts older than this/)).toBeVisible();
    const org = await call(await adminToken(), orgPath(w.slug));
    expect(org.recording_retention_days).toBe(90);
  });

  test("deleting a person's data needs their address typed, and removes their details", async () => {
    const w = world();
    const email = `erase-me-${stamp()}@example.com`;
    const token = await adminToken();
    const made = await call(token, orgPath(w.slug, "/trainees"), { method: "POST", body: { email, first_name: "Erase", last_name: "Me" } });
    await openPage(admin, `/app/${w.slug}/trainees`);
    await admin.getByRole("searchbox").fill(email);
    await admin.getByRole("row", { name: new RegExp(email) }).getByRole("button", { name: "Delete data" }).click();
    const dialog = admin.getByRole("dialog");
    const confirm = dialog.getByRole("button", { name: "Delete their data" });
    await expect(confirm).toBeDisabled();
    await dialog.getByLabel(`Type ${email} to confirm`).fill(email.toUpperCase());
    await expect(confirm).toBeEnabled();
    await confirm.click();
    await expect(admin.getByText(/permanently removed/)).toBeVisible();
    const page = await call(token, orgPath(w.slug, "/trainees?limit=100"));
    const after = (page.items as { id: string; anonymised: boolean }[]).find((row) => row.id === (made.id as string));
    expect(after?.anonymised).toBe(true);
  });
});

async function newContext(browser: Browser, role: "admin" | "trainee") {
  const context = await browser.newContext();
  await signedInAs(context, role);
  return context;
}
