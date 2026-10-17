import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { nextAfterSignIn } from "@/foundation/session/sessionUser";

describe("returning after sign-in", () => {
  it("takes the same person back to where their session ended", () => {
    assert.equal(nextAfterSignIn(new URLSearchParams("next=/app/kings/sittings"), "user-a", "user-a"), "/app/kings/sittings");
  });

  it("does not hand one person's page to somebody else", () => {
    assert.equal(nextAfterSignIn(new URLSearchParams("next=/app/kings/sittings"), "user-a", "user-b"), null);
  });

  it("follows a link when this tab has held no session", () => {
    assert.equal(nextAfterSignIn(new URLSearchParams("next=/app/kings/sittings"), null, "user-b"), "/app/kings/sittings");
  });
});
