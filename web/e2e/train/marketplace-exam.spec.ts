import { expect, test } from "@playwright/test";
import { call, login, PASSWORD, register, stamp } from "../support/api";
import { holdOnly } from "../support/db";
import { dismissOverlays, openPage, signedInAs } from "../support/session";

// Signed up for PLAB, then bought SCA. Every signed-in screen must ask about the exam the person
// holds: the marketplace listed and claimed PLAB slots and the api refused each with `not_entitled`.
test("TRAIN-12 a person who signed up for one exam and holds another can claim a marketplace slot", async ({ page, context }) => {
  const id = stamp();
  const owner = `e2e-mkt-owner-${id}@example.com`;
  const taker = `e2e-mkt-taker-${id}@example.com`;
  await register(owner, "Mkt Owner");
  await register(taker, "Mkt Taker");
  holdOnly(owner, "sca", "sca");
  holdOnly(taker, "sca", "plab");

  const ownerToken = await login(owner, PASSWORD);
  const slot = await call(ownerToken, "/api/v1/marketplace/slots", {
    method: "POST",
    body: { exam_code: "sca", starts_at: new Date(Date.now() + 2 * 3600_000).toISOString() },
  });

  const takerToken = await login(taker, PASSWORD);
  const refusals: string[] = [];
  page.on("response", (response) => {
    if (response.url().includes("/api/v1/marketplace") && response.status() === 403) refusals.push(response.url());
  });

  await signedInAs(context, { email: taker, password: PASSWORD });
  await openPage(page, "/app/me/marketplace");
  await dismissOverlays(page);

  await page.getByRole("button", { name: "Claim slot" }).first().click();
  const claim = page.waitForResponse((response) => response.url().includes(`/marketplace/slots/${slot.id as string}/claim`));
  await page.getByRole("button", { name: "Claim", exact: true }).click();
  expect((await claim).status()).toBe(201);

  await expect(page.getByText(/not_entitled|do not have access|not have access/i)).toHaveCount(0);
  const claimed = await call(takerToken, "/api/v1/me/peer-sessions");
  expect((claimed.items as { post_id?: string }[]).length).toBeGreaterThan(0);
  expect(refusals).toEqual([]);
});
