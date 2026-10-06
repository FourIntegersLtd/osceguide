import assert from "node:assert/strict";
import test from "node:test";
import { roleLabel } from "@/foundation/session/roles";
import {
  formatDetail,
  humanise,
  jobTaskLabel,
  messageSourceLabel,
  rolesForOrgType,
  MEMBER_ROLES,
  SEAT_ROLES,
  oneOptionPerLabel,
} from "@/domains/platform/support/labels";

test("identifiers read as words", () => {
  assert.equal(humanise("membership.added"), "Membership added");
  assert.equal(humanise("org.mfa_policy_changed"), "Org mfa policy changed");
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

test("every admin role reads as Admin, and an unknown role is shown as it came", () => {
  assert.equal(roleLabel("institution_admin"), "Admin");
  assert.equal(roleLabel("partner_admin"), "Admin");
  assert.equal(roleLabel("examiner_lead", humanise("examiner_lead")), "Examiner lead");
  assert.equal(roleLabel(null), "Member");
});

test("a menu offers one option per label, and a seat is the tenant admin only", () => {
  assert.deepEqual(rolesForOrgType(SEAT_ROLES, "institution"), ["institution_admin"]);
  const fitting = rolesForOrgType(MEMBER_ROLES, "institution");
  assert.deepEqual(oneOptionPerLabel(fitting, ["institution_admin"]), [
    "owner",
    "institution_admin",
    "supervisor",
    "trainee",
  ]);
  assert.deepEqual(oneOptionPerLabel(fitting, ["admin", "institution_admin"]), [
    "owner",
    "admin",
    "supervisor",
    "trainee",
  ]);
});
