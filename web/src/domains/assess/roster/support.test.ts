import assert from "node:assert/strict";
import test from "node:test";
import type { Trainee } from "@/domains/assess/api";
import { traineeStatus } from "@/domains/assess/roster/support";

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
