import { expect, test } from "@playwright/test";
import { openPage, signedInAs } from "../support/session";

// TRAIN-3: a learner sets up an AI practice session and reaches the screen
// where they would start it. The consultation itself is a LiveKit voice room and
// cannot run here, so the journey stops at the pre-start screen: rules and the
// microphone check are shown, nothing is started, and nothing is left running.
test("TRAIN-3 create a practice session and reach the pre-start screen", async ({ page, context }) => {
  await signedInAs(context, "consumer");
  const started: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "POST" && /\/api\/v1\/(attempts|voice)/.test(request.url())) started.push(request.url());
  });

  await openPage(page, "/app/me/mocks");
  await expect(page.getByRole("heading", { name: "You have completed 0 of 3 free stations" })).toBeVisible();
  // The session name is generated ("Session 1") and shown as text, not a field.
  await expect(page.getByText(/^Session \d+$/)).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Session name" })).toHaveCount(0);
  await page.getByRole("button", { name: "Create session" }).click();

  await expect(page.getByRole("heading", { level: 1, name: /^Session \d+$/ })).toBeVisible();
  await expect(page.getByText("14 min", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Rules" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Microphone check" })).toBeVisible();

  // It is kept on the list of sessions.
  await openPage(page, "/app/me/mocks/list");
  await expect(page.getByRole("link", { name: /Session \d+/ })).toBeVisible();
  // Viewing a session must not open an attempt or a voice room by itself.
  expect(started).toEqual([]);
});
