import assert from "node:assert/strict";
import test from "node:test";
import type { Trainee } from "@/domains/assess/api";
import { PlatformError } from "@/foundation/platform-client";
import { cohortName, deleteLead, rosterErrorMessage, rosterTabs, traineeStatus } from "@/domains/assess/roster/support";
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
    stations_sat: 0,
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


test("a supervisor is not offered the Exam access tab, which the API closes to admins", () => {
  assert.deepEqual(rosterTabs(false).map((t) => t.key), ["trainees", "add", "groups"]);
  assert.deepEqual(rosterTabs(true).map((t) => t.key), ["trainees", "add", "groups", "access"]);
});

test("the delete prompt says up front when Revoke is the option that will work", () => {
  assert.match(deleteLead("Ada", 3), /has sat 3 stations.*Revoke/);
  assert.doesNotMatch(deleteLead("Ada", 0), /has sat/);
});

test("a reload fetches only the lists marked stale", async () => {
  const calls: string[] = [];
  const fetchers = {
    trainees: async () => (calls.push("trainees"), [] as RosterData["trainees"]),
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
    "You have sent a lot of invitation emails just now. Wait a while, then try again.",
  );
  assert.equal(
    rosterErrorMessage(refused(429, "too_many_requests", { retry_after: 1500 }), "ada@example.com"),
    "You have sent a lot of invitation emails just now. Try again in 25 minutes.",
  );
  assert.equal(rosterErrorMessage(refused(500, "internal_error"), "a@b.c"), "raw server text");
});

test("a trainee with no group reads 'No group', not None", () => {
  assert.equal(cohortName([], null), "No group");
});
