import assert from "node:assert/strict";
import { test } from "node:test";
import { CONSENT_DOCUMENT, CONSENT_REQUIRED } from "@/capabilities/account/settings/checkoutConsent";

test("the unticked-box error names the document the checkbox does", () => {
  assert.equal(CONSENT_DOCUMENT, "Terms of Service");
  assert.equal(
    CONSENT_REQUIRED,
    "You must agree to the Terms of Service, including our No Refund Policy, before proceeding.",
  );
  assert.ok(!CONSENT_REQUIRED.includes("Privacy Policy"));
  assert.ok(!/[–—]/.test(CONSENT_REQUIRED));
});
