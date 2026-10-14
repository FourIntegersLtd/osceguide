import assert from "node:assert/strict";
import { test } from "node:test";
import { tabsFor } from "@/capabilities/account/settings/settingsTabs";

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
