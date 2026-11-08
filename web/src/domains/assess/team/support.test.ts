import assert from "node:assert/strict";
import test from "node:test";
import { EMPLOYER_WORDS, INSTITUTION_WORDS } from "@/capabilities/assess-words/vocabulary";
import {
  assessorStatus,
  assignableRoles,
  lastAdminMessage,
  roleHelp,
  staffRoleLabel,
  teamCopy,
} from "@/domains/assess/team/support";
import type { Membership } from "@/domains/assess/team/api";

const member = (over: Partial<Membership>) => ({ id: "m", user_id: "u", role: "supervisor", status: "active", ...over }) as Membership;

test("roles read Administrator and Assessor for an employer, unchanged for an institution", () => {
  assert.equal(staffRoleLabel("admin", EMPLOYER_WORDS), "Administrator");
  assert.equal(staffRoleLabel("supervisor", EMPLOYER_WORDS), "Assessor");
  assert.equal(staffRoleLabel("admin", INSTITUTION_WORDS), "Admin");
  assert.equal(staffRoleLabel("supervisor", INSTITUTION_WORDS), "Supervisor");
});

test("the employer's role help and last-administrator refusal are the board's words", () => {
  assert.equal(roleHelp(EMPLOYER_WORDS), "Assessors mark and run rotations. Administrators also manage exams, candidates and billing.");
  assert.match(lastAdminMessage(EMPLOYER_WORDS), /^You are the only administrator\./);
  assert.match(lastAdminMessage(INSTITUTION_WORDS), /^That would leave the organisation with no admin/);
});

test("assessor status is Active, Invited or Removed", () => {
  assert.deepEqual(assessorStatus(member({})), { label: "Active", tone: "ok" });
  assert.deepEqual(assessorStatus(member({ invited: true })), { label: "Invited", tone: "warn" });
  assert.deepEqual(assessorStatus(member({ status: "revoked" })), { label: "Removed", tone: "neutral" });
});

test("team copy: employer words, and the institution's unchanged", () => {
  const hire = teamCopy(EMPLOYER_WORDS);
  assert.equal(hire.invite, "Invite an assessor");
  assert.equal(hire.emptyBody, "Invite an assessor so somebody can run a rotation.");
  assert.equal(hire.revoke, "Remove access");
  assert.equal(hire.send, "Send invitation");
  assert.equal(hire.bulkDone(2, 3), "Access removed for 2 of 3 assessors.");
  const inst = teamCopy(INSTITUTION_WORDS);
  assert.equal(inst.invite, "Invite staff");
  assert.equal(inst.revoke, "Revoke");
  assert.equal(inst.send, "+ Add person");
  assert.equal(inst.bulkDone(2, 3), "Access removed for 2 of 3 staff.");
  assert.equal(inst.readOnly, "Supervisor (read only)");
});

test("only an employer can invite a lead assessor; an institution offers what it always did", () => {
  assert.deepEqual(assignableRoles(EMPLOYER_WORDS), ["supervisor", "gp_lead", "admin"]);
  assert.deepEqual(assignableRoles(INSTITUTION_WORDS), ["supervisor", "admin"]);
});

test("the lead assessor reads Lead assessor on hire and has its own help line", () => {
  assert.equal(staffRoleLabel("gp_lead", EMPLOYER_WORDS), "Lead assessor");
  assert.equal(staffRoleLabel("gp_lead", INSTITUTION_WORDS), "GP lead");
  assert.equal(roleHelp(EMPLOYER_WORDS, "gp_lead"), "A lead assessor settles disagreements between two assessors on the same station.");
  assert.equal(roleHelp(EMPLOYER_WORDS, "supervisor"), roleHelp(EMPLOYER_WORDS));
});
