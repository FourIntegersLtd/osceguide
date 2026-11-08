import { expect, test, type Page } from "@playwright/test";
import { buildSitting, type BuiltSitting } from "../support/sitting";
import { openPage, signedInAs } from "../support/session";
import { world } from "../support/world";

// ASSESS-2 and ASSESS-3: the supervisor runs a circuit and the trainee sits it.
//
// The spoken part cannot run here (no LiveKit credentials), so it is driven
// through its seams: the trainee's brief and the "Join" control are checked but
// not pressed, and "Next station", which opens the patient's voice room, is
// asserted to fail clearly instead of hanging. Ending the circuit then closes
// the sitting with the slot skipped, which is what the marking journey starts from.
test.describe.serial("ASSESS-2/3 run a circuit", () => {
  let sitting: BuiltSitting;
  let admin: Page;
  let trainee: Page;

  test.beforeAll(async ({ browser }) => {
    sitting = await buildSitting("Circuit run", "exam");
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

  test("ASSESS-2 the trainee waits, then the supervisor starts and the brief opens", async () => {
    const w = world();
    await openPage(trainee, `/app/${w.slug}/trainee/sittings/${sitting.id}`);
    await expect(trainee.getByText("Your station opens when your supervisor starts it.")).toBeVisible();

    await openPage(admin, `/app/${w.slug}/circuits/${sitting.circuitId}`);
    await admin.getByRole("button", { name: "Start circuit" }).click();
    await expect(admin.getByText("Reading time").first()).toBeVisible();

    // The trainee's own screen follows the circuit: station open, brief readable, Join offered.
    await trainee.reload({ waitUntil: "domcontentloaded" });
    await expect(trainee.getByRole("heading", { name: "Your station is open" })).toBeVisible();
    await expect(trainee.getByText("Patient Biodata")).toBeVisible();
    await expect(trainee.getByRole("button", { name: /Join/ })).toBeVisible();
  });

  test("ASSESS-3 without a voice room the supervisor is told so, and can end the circuit", async () => {
    const w = world();
    await openPage(admin, `/app/${w.slug}/circuits/${sitting.circuitId}`);
    await admin.getByRole("button", { name: "Next station" }).click();
    // voice_unavailable (503): a visible message, and the circuit is still controllable.
    await expect(admin.getByRole("alert").filter({ hasText: /voice|room|LiveKit|unavailable/i }).first()).toBeVisible();
    // End sits in the "⋯" menu, last, with the other less common controls.
    await admin.getByRole("button", { name: "More circuit controls" }).click();
    await expect(admin.getByRole("menuitem", { name: "End circuit" })).toBeVisible();

    await admin.getByRole("menuitem", { name: "End circuit" }).click();
    await admin.getByRole("dialog").getByRole("button", { name: "End the circuit" }).click();

    await openPage(admin, `/app/${w.slug}/sittings/${sitting.id}`);
    await expect(admin.getByText("Completed", { exact: true }).first()).toBeVisible();
    await openPage(trainee, `/app/${w.slug}/trainee/sittings/${sitting.id}`);
    await expect(trainee.getByText("A finished station cannot be re-entered.")).toBeVisible();
  });
});
