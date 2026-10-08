import assert from "node:assert/strict";
import { test } from "node:test";
import { tabsFor } from "@/capabilities/account/settings/settingsTabs";

test("every consumer account sees the Referrals tab, as checkout and the code route already allow", () => {
  assert.deepEqual(
    tabsFor("train").map((tab) => tab.id),
    ["profile", "preferences", "exam", "payments", "referrals", "memory"],
  );
});

test("staff settings carry no Referrals tab", () => {
  assert.deepEqual(
    tabsFor("platform").map((tab) => tab.id),
    ["account", "security", "data"],
  );
});
