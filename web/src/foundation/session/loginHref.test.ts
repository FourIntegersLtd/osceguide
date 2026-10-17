import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { loginHref, signedOutDestination } from "@/foundation/session/loginHref";

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

describe("where a sign-out sends you", () => {
  it("applies only on the page the person signed out from", () => {
    const signedOut = { to: "/login?deleted=1", from: "/app/me/settings" };
    assert.equal(signedOutDestination(signedOut, "/app/me/settings"), "/login?deleted=1");
  });

  it("is spent once the person has moved on, so a later protected page keeps its next", () => {
    const signedOut = { to: "/login?deleted=1", from: "/app/me/settings" };
    assert.equal(signedOutDestination(signedOut, "/app/me/dashboard"), null);
    assert.equal(signedOutDestination(null, "/app/me/dashboard"), null);
  });
});
