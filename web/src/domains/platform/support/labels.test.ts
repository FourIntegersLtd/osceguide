import assert from "node:assert/strict";
import test from "node:test";
import {
  formatDetail,
  humanise,
  jobTaskLabel,
  messageSourceLabel,
  roleLabel,
  rolesForOrgType,
  MEMBER_ROLES,
} from "@/domains/platform/support/labels";

test("identifiers read as words", () => {
  assert.equal(humanise("membership.added"), "Membership added");
  assert.equal(humanise("org.mfa_policy_changed"), "Org mfa policy changed");
  assert.equal(roleLabel("institution_admin"), "Institution administrator");
  assert.equal(roleLabel("examiner_lead"), "Examiner lead");
  assert.equal(jobTaskLabel("app.features.sittings.jobs.sweep_circuits"), "Sweep circuits");
});

test("details drop the empty ones and name the rest", () => {
  assert.equal(
    formatDetail({ status: "active", previous_status: null, require_staff_mfa: false, reason: "never joined" }),
    "Status: Active · Require staff mfa: No · Reason: never joined",
  );
  assert.equal(formatDetail(null), "");
});

test("message sources are named, and an unknown one is shown as it came", () => {
  assert.equal(messageSourceLabel("messages-screen"), "In-app message");
  assert.equal(messageSourceLabel("contact"), "Contact form");
  assert.equal(messageSourceLabel("newsletter"), "newsletter");
});

test("a menu offers only the roles that fit the organisation's type", () => {
  assert.deepEqual(rolesForOrgType(MEMBER_ROLES, "institution"), [
    "owner",
    "admin",
    "institution_admin",
    "supervisor",
    "trainee",
  ]);
  assert.deepEqual(rolesForOrgType(MEMBER_ROLES, "partner"), [
    "owner",
    "admin",
    "partner_admin",
    "supervisor",
    "practice_user",
  ]);
});
