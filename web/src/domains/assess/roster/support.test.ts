import assert from "node:assert/strict";
import test from "node:test";
import type { Trainee } from "@/domains/assess/api";
import { PlatformError } from "@/foundation/platform-client";
import { cohortDeleteLead, cohortName, deleteLead, rosterErrorMessage, traineeStatus } from "@/domains/assess/roster/support";
import { loadRoster, type RosterData, type RosterPart } from "@/domains/assess/roster/useRosterData";

function trainee(over: Partial<Trainee> = {}): Trainee {
  return {
    id: "t1",
    email: "ada@example.com",
    first_name: "Ada",
    last_name: null,
    cohort_id: null,
    user_id: "u1",
    access_revoked: false,
    anonymised: false,
    invitation_pending: false,
    is_member: true,
    programme_names: [],
    revision: 1,
    stations_sat: 0,
    temporary_password_applied: false,
    ...over,
  };
}

test("a row with no account is only added, and says so", () => {
  assert.deepEqual(traineeStatus(trainee({ user_id: null })), {
    stage: "added",
    label: "Added",
    attention: "Added, no account yet",
  });
});

test("an unused account is invited and stuck until it is accepted", () => {
  assert.deepEqual(traineeStatus(trainee({ invitation_pending: true })), {
    stage: "invited",
    label: "Invited",
    attention: "Invited, not accepted",
  });
});

test("an accepted account that holds no membership is flagged", () => {
  assert.deepEqual(traineeStatus(trainee({ is_member: false })), {
    stage: "accepted",
    label: "Accepted",
    attention: "Accepted, not a member",
  });
});

test("a member with nothing booked is fine, and one on a sitting is booked", () => {
  assert.deepEqual(traineeStatus(trainee()), { stage: "member", label: "Member", attention: null });
  assert.deepEqual(traineeStatus(trainee({ programme_names: ["SCA"] })), {
    stage: "booked",
    label: "Booked",
    attention: null,
  });
});

test("revoked access is flagged whatever step was reached", () => {
  assert.equal(traineeStatus(trainee({ access_revoked: true, programme_names: ["SCA"] })).attention, "Access revoked");
});


test("the delete prompt says up front when Revoke is the option that will work", () => {
  assert.match(deleteLead("Ada", 3), /has sat 3 stations.*Revoke/);
  assert.doesNotMatch(deleteLead("Ada", 0), /has sat/);
});

test("the cohort delete prompt counts the sittings that detach", () => {
  assert.match(cohortDeleteLead("2027 intake", 3), /3 sittings held for it are kept but no longer belong to any year group/);
  assert.match(cohortDeleteLead("2027 intake", 1), /1 sitting held for it is kept/);
  assert.match(cohortDeleteLead("2027 intake", 0), /No sittings are held for it/);
});

test("a reload fetches only the lists marked stale", async () => {
  const calls: string[] = [];
  const fetchers = {
    trainees: async () => (calls.push("trainees"), { rows: [], total: 0, cursor: null } as RosterData["trainees"]),
    cohorts: async () => (calls.push("cohorts"), [] as RosterData["cohorts"]),
    groups: async () => (calls.push("groups"), [] as RosterData["groups"]),
  };
  const cache: { slug?: string; data?: RosterData } = {};
  await loadRoster(cache, "kings", new Set<RosterPart>(["trainees", "cohorts", "groups"]), fetchers);
  assert.deepEqual(calls, ["trainees", "cohorts", "groups"]);
  calls.length = 0;
  await loadRoster(cache, "kings", new Set<RosterPart>(["groups"]), fetchers);
  assert.deepEqual(calls, ["groups"]);
  calls.length = 0;
  await loadRoster(cache, "other", new Set<RosterPart>(["groups"]), fetchers);
  assert.deepEqual(calls, ["trainees", "cohorts", "groups"]);
});

test("a duplicate add and a rate-limited resend are said plainly", () => {
  const refused = (status: number, code: string, details?: Record<string, unknown>) =>
    new PlatformError(status, { code, message: "raw server text", details } as never);
  assert.equal(
    rosterErrorMessage(refused(409, "trainee_exists"), "ada@example.com"),
    "ada@example.com is already on this roster.",
  );
  assert.equal(
    rosterErrorMessage(refused(429, "too_many_requests"), "ada@example.com"),
    "raw server text",
  );
  assert.equal(
    rosterErrorMessage(refused(429, "too_many_requests", { retry_after: 1500 }), "ada@example.com"),
    "Too many attempts. Try again in 25 minutes.",
  );
  assert.equal(rosterErrorMessage(refused(500, "internal_error"), "a@b.c"), "raw server text");
});

test("a trainee with no group reads 'No group', not None", () => {
  assert.equal(cohortName([], null), "No group");
});
