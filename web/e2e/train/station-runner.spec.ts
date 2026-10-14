import { expect, test } from "@playwright/test";
import { openPage, signedInAs } from "../support/session";

// TRAIN-9: the screens a learner meets before the consultation. The consultation itself is a
// LiveKit room and cannot run here, so the journey stops once the brief is on screen.
// Ending a consultation on a station that is not the last is decided by `endOutcome`
// (src/capabilities/station-runner/sessionEnd.test.ts), because no voice room runs in CI.
test("TRAIN-9 Ready to start can go back, and the brief is one row of controls", async ({ page, context }) => {
  // Its own learner: the attempt this starts keeps the session undeletable (SetHasAttemptsError).
  await signedInAs(context, "runner");
  await openPage(page, "/app/me/mocks");
  await page.getByRole("button", { name: "Create session" }).click();
  const heading = page.getByRole("heading", { level: 1, name: /^Session \d+$/ });
  await expect(heading).toBeVisible();
  const session = page.url();

  await page.getByRole("link", { name: "Start Session" }).first().click();
  await expect(page.getByRole("heading", { name: "Ready to start?" })).toBeVisible();
  await page.getByRole("button", { name: "Back", exact: true }).click();
  await expect(heading).toBeVisible();
  expect(page.url()).toBe(session);

  await page.getByRole("link", { name: "Start Session" }).first().click();
  await page.getByRole("button", { name: "Start", exact: true }).click();
  const start = page.getByRole("button", { name: "Start simulation" });
  await expect(start).toBeVisible();
  // Reading time and Consultation were two doors to the same place: no step tabs before it starts.
  await expect(page.getByRole("navigation", { name: "Station steps" })).toHaveCount(0);
  const skip = page.getByRole("button", { name: /^Skip to (next station|complete session)$/ });
  const [a, b] = [await start.boundingBox(), await skip.boundingBox()];
  expect(a && b && Math.abs(a.y + a.height / 2 - (b.y + b.height / 2)) < 8, "start and skip share a row").toBe(true);

  // On a phone the row wraps; nothing scrolls sideways.
  await page.setViewportSize({ width: 360, height: 740 });
  await expect(skip).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
