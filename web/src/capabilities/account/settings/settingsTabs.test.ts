import assert from "node:assert/strict";
import { test } from "node:test";
import { arrangeTabs, tabsFor } from "@/capabilities/account/settings/settingsTabs";

test("an organisation's own tabs open the strip, then the person's, then Invoices, as on the Settings board", () => {
  const extras = [
    { id: "organisation", label: "Organisation" },
    { id: "sso", label: "Single sign-on" },
    { id: "provisioning", label: "Automatic user sync" },
    { id: "invoices", label: "Invoices", after: true },
  ];
  assert.deepEqual(
    arrangeTabs(tabsFor("assess"), extras).map((tab) => tab.label),
    ["Organisation", "Single sign-on", "Automatic user sync", "Your account", "Preferences", "Invoices"],
  );
});

test("a supervisor, with no organisation tabs, sees Your account and Preferences only", () => {
  assert.deepEqual(
    arrangeTabs(tabsFor("assess"), []).map((tab) => tab.label),
    ["Your account", "Preferences"],
  );
});

test("a learner's strip keeps its Profile label", () => {
  assert.equal(tabsFor("train")[0]?.label, "Profile");
});

test("every consumer account sees the Referrals tab and no Exam tab (the exam type is on Profile)", () => {
  assert.deepEqual(
    tabsFor("train").map((tab) => tab.id),
    ["profile", "preferences", "payments", "referrals"],
  );
});

test("staff settings carry no Referrals tab", () => {
  assert.deepEqual(
    tabsFor("platform").map((tab) => tab.id),
    ["account", "security", "data"],
  );
});

test("institution, hire and partner settings carry no Payments or Referrals tab", () => {
  for (const surface of ["assess", "hire", "partner"]) {
    assert.deepEqual(
      tabsFor(surface).map((tab) => tab.id),
      ["profile", "preferences"],
      surface,
    );
  }
});
