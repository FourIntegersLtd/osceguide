import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { loginHref } from "@/foundation/session/loginHref";

describe("login redirect", () => {
  it("does not call a first visit an expired session", () => {
    assert.equal(loginHref("/app/me/dashboard", false), "/login?next=%2Fapp%2Fme%2Fdashboard");
    assert.equal(loginHref("/app/me/dashboard", false).includes("session_expired"), false);
  });

  it("names the reason only when a stored token was refused", () => {
    assert.equal(
      loginHref("/app/me/settings", true),
      "/login?next=%2Fapp%2Fme%2Fsettings&reason=session_expired",
    );
  });
});
