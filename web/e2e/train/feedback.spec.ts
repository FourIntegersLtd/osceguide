import { expect, test } from "@playwright/test";
import { seedMarkedPracticeAttempt } from "../support/db";
import { openPage, signedInAs } from "../support/session";
import { world } from "../support/world";

// TRAIN-4: after a station is marked the learner reads the feedback and the
// dashboard counts it. The marking itself needs a spoken transcript, so the
// marked attempt is a database seam (support/db.ts).
test("TRAIN-4 a marked station shows feedback and moves the dashboard", async ({ page, context }) => {
  const learner = world().accounts.consumer;
  const attemptId = seedMarkedPracticeAttempt(learner.email);
  await signedInAs(context, "consumer");

  await openPage(page, `/app/me/attempts/${attemptId}`);
  await expect(page).toHaveURL(new RegExp(`/app/me/attempts/${attemptId}|/practise`));
  await expect(page.getByText(/Your mark/i).first()).toBeVisible();
  await expect(page.getByText("Shall we start with what brought you in?")).toBeVisible();

  await openPage(page, "/app/me/dashboard");
  await expect(page.getByText("1 station attempted")).toBeVisible();
  await expect(page.getByText("No assessments yet")).toHaveCount(0);
});
