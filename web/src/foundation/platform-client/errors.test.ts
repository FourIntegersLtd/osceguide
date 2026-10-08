import assert from "node:assert/strict";
import { test } from "node:test";
import { PlatformError, rateLimitMessage } from "@/foundation/platform-client/errors";

function tooMany(retryAfter?: number) {
  return new PlatformError(429, {
    code: "too_many_requests",
    message: "Too many attempts. Wait a moment and try again.",
    details: retryAfter === undefined ? null : { retry_after: retryAfter, limit: "outbound-email" },
    request_id: null,
  });
}

test("a rate limit says how long to wait, in minutes, when the server gave retry_after (S-26)", () => {
  assert.equal(rateLimitMessage(tooMany(1500)), "Too many attempts. Try again in 25 minutes.");
});

test("a short wait rounds up to one minute, singular", () => {
  assert.equal(rateLimitMessage(tooMany(20)), "Too many attempts. Try again in 1 minute.");
});

test("without retry_after the server sentence stays", () => {
  assert.equal(rateLimitMessage(tooMany()), "Too many attempts. Wait a moment and try again.");
});

test("any other failure is not a rate limit", () => {
  assert.equal(rateLimitMessage(new Error("boom")), null);
});
