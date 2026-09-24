import assert from "node:assert/strict";
import test from "node:test";
import { MAX_TEAM_UPLOAD, parseStaffCsv, teamSkipReason } from "@/domains/assess/team/csv";

test("the two columns the old staff sheet required are read whatever their case", () => {
  const parsed = parseStaffCsv(" Email , Role \nTutor@Hospital.NHS.UK, Supervisor ");
  assert.equal(parsed.error, null);
  assert.deepEqual(parsed.rows, [{ email: "tutor@hospital.nhs.uk", role: "supervisor" }]);
});

test("an administrator is a role, not a third thing the backend has to guess", () => {
  const parsed = parseStaffCsv("email,role\na@b.uk,Administrator");
  assert.deepEqual(parsed.rows, [{ email: "a@b.uk", role: "admin" }]);
});

test("a file with no email column is refused rather than half-imported", () => {
  const parsed = parseStaffCsv("name,role\nAmina,supervisor");
  assert.equal(parsed.rows.length, 0);
  assert.match(parsed.error ?? "", /email/);
});

test("a row with no usable address is reported by line number, not dropped silently", () => {
  const parsed = parseStaffCsv("email,role\na@b.uk,admin\n,admin\nnot-an-address,supervisor");
  assert.equal(parsed.rows.length, 1);
  assert.deepEqual(parsed.skippedLines, [3, 4]);
  assert.deepEqual(parsed.badRoles, []);
});

test("a role this organisation cannot grant is reported rather than invited as", () => {
  // `owner` is created with the organisation and `trainee` is not a staff role;
  // posting either would be a write the backend refuses for the whole batch.
  const parsed = parseStaffCsv("email,role\na@b.uk,owner\nc@d.uk,");
  assert.deepEqual(parsed.rows, []);
  assert.deepEqual(
    parsed.badRoles.map((row) => row.line),
    [2, 3],
  );
  assert.match(parsed.error ?? "", /role/);
});

test("an upload over the backend's cap is refused before anything is posted", () => {
  const lines = ["email,role"];
  for (let index = 0; index <= MAX_TEAM_UPLOAD; index += 1) {
    lines.push(`tutor${index}@hospital.nhs.uk,supervisor`);
  }
  const parsed = parseStaffCsv(lines.join("\n"));
  assert.deepEqual(parsed.rows, []);
  assert.match(parsed.error ?? "", new RegExp(String(MAX_TEAM_UPLOAD)));
});

test("a skipped row is explained in words, not in a code", () => {
  assert.equal(teamSkipReason("membership_exists"), "already on the team with that role");
  assert.equal(teamSkipReason("something_new"), "something new");
});
