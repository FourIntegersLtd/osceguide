import assert from "node:assert/strict";
import { test } from "node:test";
import { PlatformError } from "@/foundation/platform-client/errors";
import { checkoutErrorMessage } from "@/capabilities/account/settings/checkoutErrors";

const refused = (status: number, code: string, message = "Server words") =>
  new PlatformError(status, { code, message } as never);

test("a second purchase of a held exam says so", () => {
  assert.equal(
    checkoutErrorMessage(refused(409, "already_purchased"), "help@x.test"),
    "Server words",
  );
});

test("a plan for another exam is told apart from a bad referral code", () => {
  assert.equal(
    checkoutErrorMessage(refused(404, "plan_not_available"), "help@x.test"),
    "That plan is not available for your exam. Choose another plan.",
  );
  assert.equal(
    checkoutErrorMessage(refused(404, "referral_not_found"), "help@x.test"),
    "That referral code is not valid. Check it, or clear it to pay the full price.",
  );
});

test("any other failure says no money moved and where to write", () => {
  assert.equal(
    checkoutErrorMessage(refused(503, "checkout_failed", "Payments are down"), "help@x.test"),
    "Payments are down No money has left your account. Please try again or email help@x.test.",
  );
  assert.equal(
    checkoutErrorMessage(new Error("boom"), "help@x.test"),
    "We could not start your payment. No money has left your account. Please try again or email help@x.test.",
  );
});
