import assert from "node:assert/strict";
import test from "node:test";
import {
  addCandidatesBlocked,
  addCandidatesLabel,
  candidatePills,
  candidateStatus,
  duplicateWarning,
  filterByPill,
  parsePastedEmails,
} from "@/domains/assess/people/candidatesView";

const row = (over: Partial<Parameters<typeof candidateStatus>[0] & { cohort_id: string | null }> = {}) => ({
  cohort_id: "n" as string | null,
  user_id: "u" as string | null,
  invitation_pending: false,
  access_revoked: false,
  is_member: true,
  ...over,
});

test("a candidate is Joined, Invited or Access removed", () => {
  assert.deepEqual(candidateStatus(row()), { label: "Joined", tone: "ok" });
  assert.deepEqual(candidateStatus(row({ invitation_pending: true })), { label: "Invited", tone: "warn" });
  assert.deepEqual(candidateStatus(row({ user_id: null })), { label: "Invited", tone: "warn" });
  assert.deepEqual(candidateStatus(row({ access_revoked: true })), { label: "Access removed", tone: "neutral" });
});

test("the pills are All, each intake, Invited not joined, with counts only when every row is loaded", () => {
  const rows = [row(), row({ user_id: null }), row({ cohort_id: "o" })];
  const cohorts = [{ id: "n", name: "November intake" }, { id: "o", name: "October intake" }];
  assert.deepEqual(candidatePills(rows, cohorts, 3, false).map((p) => p.label), ["All 3", "November intake 2", "October intake 1", "Invited, not joined 1"]);
  assert.deepEqual(candidatePills(rows, cohorts, 36, true).map((p) => p.label), ["All 36", "November intake", "October intake", "Invited, not joined"]);
  assert.equal(filterByPill(rows, "invited").length, 1);
  assert.equal(filterByPill(rows, { intake: "o" }).length, 1);
  assert.equal(filterByPill(rows, "all").length, 3);
});

test("pasted emails split on lines, skip candidates already listed, and say so", () => {
  const parsed = parsePastedEmails("priya.shah@mail.com\ntom.reid@mail.com\nTOM.reid@mail.com\nnope", ["tom.reid@mail.com"]);
  assert.deepEqual(parsed, { emails: ["priya.shah@mail.com"], invalid: ["nope"], duplicates: ["tom.reid@mail.com"] });
  assert.equal(duplicateWarning(parsed.duplicates), "tom.reid@mail.com is already a candidate. We will skip it.");
  assert.equal(duplicateWarning(["a@b.co", "c@d.co"]), "2 addresses are already candidates. We will skip them.");
  assert.equal(duplicateWarning([]), null);
});

test("the primary names how many it adds, and a disabled one says why", () => {
  assert.equal(addCandidatesLabel(0), "Add candidates");
  assert.equal(addCandidatesLabel(1), "Add 1 candidate");
  assert.equal(addCandidatesLabel(3), "Add 3 candidates");
  assert.equal(addCandidatesBlocked(parsePastedEmails("", []), false), "Enter at least one email address.");
  assert.equal(addCandidatesBlocked(parsePastedEmails("x", []), false), "x is not a usable email address.");
  assert.equal(addCandidatesBlocked(parsePastedEmails("a@b.co", ["a@b.co"]), false), "Every address is already a candidate.");
  assert.equal(addCandidatesBlocked(parsePastedEmails("a@b.co", []), false), null);
});
