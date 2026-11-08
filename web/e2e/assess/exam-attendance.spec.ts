// Named to run after build-sitting: this spec adds a sitting, which moves the dashboard guide ASSESS-1 expects.
import { expect, test, type Page } from "@playwright/test";
import { buildSitting, type BuiltSitting } from "../support/sitting";
import { openPage, signedInAs } from "../support/session";
import { world } from "../support/world";

// Exam-day attendance: a supervisor marks a no-show absent (reason required, recorded), the
// candidate is told plainly, and the dropped-connection re-join asks for a reason too.
const SHOTS = process.env.E2E_SHOTS ?? "";

test.describe.serial("exam-day attendance", () => {
  let sitting: BuiltSitting;
  let admin: Page;
  let trainee: Page;

  test.beforeAll(async ({ browser }) => {
    sitting = await buildSitting("Attendance", "exam");
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

  async function shot(page: Page, name: string) {
    if (SHOTS) await page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: true });
  }

  for (const [label, width, height] of [["1440", 1440, 900], ["390", 390, 844]] as const) {
    test(`mark absent needs a reason, then the candidate is told (${label})`, async () => {
      if (label === "390") sitting = await buildSitting(`Attendance ${label}`, "exam");
      await admin.setViewportSize({ width, height });
      await trainee.setViewportSize({ width, height });
      const w = world();
      await openPage(admin, `/app/${w.slug}/circuits/${sitting.circuitId}`);
      await admin.getByRole("button", { name: "More circuit controls" }).click();
      await admin.getByRole("menuitem", { name: /^Mark .* absent$/ }).click();
      const dialog = admin.getByRole("dialog");
      const commit = dialog.getByRole("button", { name: "Mark absent" });
      await expect(commit).toBeDisabled();
      await shot(admin, `admin-dialog-${label}`);
      await dialog.getByRole("textbox").fill("Did not arrive, phoned and no answer");
      await expect(commit).toBeEnabled();
      await commit.click();
      await expect(dialog).toBeHidden();

      await openPage(trainee, `/app/${w.slug}/trainee/sittings/${sitting.id}`);
      await expect(trainee.getByText("You were marked absent").first()).toBeVisible();
      await shot(trainee, `trainee-absent-${label}`);

      await openPage(admin, `/app/${w.slug}/circuits/${sitting.circuitId}`);
      await admin.getByRole("button", { name: /Changes made during the circuit/ }).click();
      await expect(admin.getByText("Marked absent").first()).toBeVisible();
      await expect(admin.getByText(/Did not arrive, phoned and no answer/)).toBeVisible();
      await shot(admin, `admin-log-${label}`);
    });
  }

  test("allow one re-join asks for a reason", async () => {
    const w = world();
    await admin.setViewportSize({ width: 1440, height: 900 });
    const live = await buildSitting("Attendance rejoin", "exam");
    await openPage(admin, `/app/${w.slug}/circuits/${live.circuitId}`);
    await admin.getByRole("button", { name: "Start circuit" }).click();
    await expect(admin.getByText("Reading time").first()).toBeVisible();
    // The live feed re-renders the console after Start and can close a menu opened too early: open it until it stays.
    const rejoin = admin.getByRole("menuitem", { name: "Allow one re-join" });
    await expect(async () => {
      if (!(await rejoin.isVisible())) await admin.getByRole("button", { name: "More circuit controls" }).click();
      await expect(rejoin).toBeVisible({ timeout: 1500 });
    }).toPass({ timeout: 15000 });
    await rejoin.click();
    await expect(admin.getByRole("dialog").getByRole("button", { name: "Allow re-join" })).toBeDisabled();
    await shot(admin, "admin-rejoin-dialog");
  });
});
