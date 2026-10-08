import assert from "node:assert/strict";
import { test } from "node:test";
import { PlatformError } from "@/foundation/platform-client/errors";
import { CONFIRM_ATTEMPTS, confirmPayment } from "@/capabilities/account/paymentConfirmation";

const noWait = async () => {};
const never = () => false;

test("a receipt for this session confirms the payment", async () => {
  assert.equal(await confirmPayment(async () => ["R-1"], noWait, never), "paid");
});

test("no receipt yet is asked again, then said to be pending, not paid", async () => {
  let asked = 0;
  const outcome = await confirmPayment(
    async () => {
      asked += 1;
      return [];
    },
    noWait,
    never,
  );
  assert.deepEqual([outcome, asked], ["pending", CONFIRM_ATTEMPTS]);
});

test("a receipt that appears on the third ask confirms it", async () => {
  let asked = 0;
  const outcome = await confirmPayment(async () => (++asked < 3 ? [] : ["R-1"]), noWait, never);
  assert.deepEqual([outcome, asked], ["paid", 3]);
});

test("a 401 stops the wait and asks for a sign-in; other failures are retried", async () => {
  const unauthenticated = new PlatformError(401, { code: "unauthenticated", message: "Sign in" });
  let asked = 0;
  assert.equal(
    await confirmPayment(
      async () => {
        asked += 1;
        throw unauthenticated;
      },
      noWait,
      never,
    ),
    "signed_out",
  );
  assert.equal(asked, 1);

  const gateway = new PlatformError(503, { code: "internal_error", message: "down" });
  asked = 0;
  const outcome = await confirmPayment(async () => (++asked < 2 ? Promise.reject(gateway) : ["R-1"]), noWait, never);
  assert.deepEqual([outcome, asked], ["paid", 2]);
});
