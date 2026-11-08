import { expect, test, type Page } from "@playwright/test";
import { ApiError, call, login, PASSWORD, switchWorkspace } from "../support/api";
import { seedMarkedSlotAttempt } from "../support/db";
import { buildSitting, endCircuit, startCircuit, type BuiltSitting } from "../support/sitting";
import { openPage, signedInAs } from "../support/session";
import { world } from "../support/world";

// ASSESS-4: after the room, the reviewer marks the station, the admin decides
// and signs off, releases the result, and only then can the candidate read it.
test.describe.serial("ASSESS-4 review, decide, release", () => {
  let sitting: BuiltSitting;
  let admin: Page;
  let trainee: Page;

  test.beforeAll(async ({ browser }) => {
    sitting = await buildSitting("Release run", "exam");
    await startCircuit(sitting);
    await endCircuit(sitting); // the voice room is skipped: the slot is closed with nothing said
    seedMarkedSlotAttempt(sitting.slotId); // db seam: what a marked spoken station leaves behind
    const adminContext = await browser.newContext();
    await signedInAs(adminContext, "admin");
    admin = await adminContext.newPage();
    const traineeContext = await browser.newContext();
    await signedInAs(traineeContext, "trainee");
    trainee = await traineeContext.newPage();
  });

  test.afterAll(async () => {
    await admin.context().close();
    await trainee.context().close();
  });

  test("the candidate reads nothing before release", async () => {
    const w = world();
    await openPage(trainee, `/app/${w.slug}/trainee/results/${sitting.id}`);
    await expect(trainee.getByText("Not released yet")).toBeVisible();
    // R-1: the api gives the candidate nothing either: an error, or the reason it is not released (T-8), never the review.
    const traineeToken = await switchWorkspace(await login(w.accounts.trainee.email, PASSWORD), w.slug);
    const answer = await call(traineeToken, `/api/v1/me/slots/${sitting.slotId}/review`).then(
      (body) => body,
      (error: ApiError) => error.status,
    );
    expect(typeof answer === "number" || (answer as { state?: string } | null)?.state === "not_released").toBe(true);
  });

  test("the reviewer rates every domain and completes the review", async () => {
    const w = world();
    await openPage(admin, `/app/${w.slug}/slots/${sitting.slotId}/review?sitting=${sitting.id}`);
    await expect(admin.getByRole("heading", { level: 1, name: "Mark this station" })).toBeVisible();
    // Every rating row offers G / A / R; rate them all Green.
    const green = admin.getByRole("button", { name: "Green", exact: true });
    for (const button of await green.all()) await button.click();
    await admin.getByRole("button", { name: "Complete review" }).click();
    await expect(admin.getByText(/Review completed/)).toBeVisible();
  });

  test("the admin decides, signs off and releases; the candidate then reads the outcome", async () => {
    const w = world();
    await openPage(admin, `/app/${w.slug}/sittings/${sitting.id}/results`);
    // An institution exam has no hiring decision: not in the table, not in the open candidate.
    await expect(admin.getByText("Hiring decision")).toHaveCount(0);
    await admin.getByRole("button", { name: "Open Tess Trainee" }).click();
    await expect(admin.getByText("Hiring decision")).toHaveCount(0);
    await admin.getByRole("button", { name: /^Pass/ }).click();
    await admin.getByRole("textbox", { name: /rationale/i }).fill("Journey: met the standard.");
    await admin.getByRole("button", { name: "Sign off" }).click();
    await expect(admin.getByRole("button", { name: "Back to draft" })).toBeVisible();
    await admin.getByRole("button", { name: "Release 1 signed-off result" }).click();
    await admin.getByRole("dialog").getByRole("button", { name: "Release" }).click();

    await openPage(trainee, `/app/${w.slug}/trainee/results/${sitting.id}`);
    await expect(trainee.getByText("Not released yet")).toHaveCount(0);
    await expect(trainee.getByText(/Pass/i).first()).toBeVisible();
  });
});
