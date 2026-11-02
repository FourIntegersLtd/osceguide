import { expect, test } from "@playwright/test";
import { seedMarkedPracticeAttempt } from "../support/db";
import { openPage, signedInAs } from "../support/session";
import { world } from "../support/world";

// TRAIN-4: after a station is marked the learner reads the feedback and the
// dashboard counts it. The marking itself needs a spoken transcript, so the
// marked attempt is a database seam (support/db.ts).
// Its own learner, not "consumer": the seeded attempt would otherwise count toward
// "consumer"'s lifetime stations-sat total that TRAIN-3 reads as "0 of 3 free stations".
test("TRAIN-4 a marked station shows feedback and moves the dashboard", async ({ page, context }) => {
  const learner = world().accounts.runner;
  const attemptId = seedMarkedPracticeAttempt(learner.email);
  await signedInAs(context, "runner");

  await openPage(page, `/app/me/attempts/${attemptId}`);
  await expect(page).toHaveURL(new RegExp(`/app/me/attempts/${attemptId}|/practise`));
  await expect(page.getByText(/Your mark/i).first()).toBeVisible();
  await expect(page.getByText("Shall we start with what brought you in?")).toBeVisible();

  await openPage(page, "/app/me/dashboard");
  await expect(page.getByText("1 station attempted")).toBeVisible();
  await expect(page.getByText("No assessments yet")).toHaveCount(0);
});
