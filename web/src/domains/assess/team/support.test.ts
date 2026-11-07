import assert from "node:assert/strict";
import test from "node:test";
import { teamRoleLabel } from "@/domains/assess/team/support";
import { EMPLOYER_WORDS, INSTITUTION_WORDS } from "@/domains/assess/vocabulary";

test("an employer's staff are assessors and lead assessors; an institution's keep their role names", () => {
  assert.equal(teamRoleLabel("supervisor", EMPLOYER_WORDS), "Assessor");
  assert.equal(teamRoleLabel("admin", EMPLOYER_WORDS), "Lead assessor");
  assert.equal(teamRoleLabel("owner", EMPLOYER_WORDS), "Owner");
  assert.equal(teamRoleLabel("supervisor", INSTITUTION_WORDS), "Supervisor");
  assert.equal(teamRoleLabel("admin", INSTITUTION_WORDS), "Admin");
});
