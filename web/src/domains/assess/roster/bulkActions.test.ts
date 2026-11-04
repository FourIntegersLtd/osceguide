import assert from "node:assert/strict";
import { afterEach, describe, it } from "node:test";
import type { Trainee } from "@/domains/assess/api";
import { resendTraineeInvitations, revokeTrainees, setTraineesCohort } from "@/domains/assess/roster/api";
import { awaitingInvitation, bulkSummary } from "@/domains/assess/roster/support";

const realFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = realFetch;
});

function ids(count: number): string[] {
  return Array.from({ length: count }, (_, index) => `t${index}`);
}

/** Answers every sent id with `outcome`, recording each request's path and body. */
function answer(outcome: string, calls: { url: string; body: Record<string, unknown> }[]) {
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    const body = JSON.parse(String(init?.body)) as { trainee_ids: string[] };
    calls.push({ url: String(input), body });
    const results = body.trainee_ids.map((trainee_id) => ({ trainee_id, outcome }));
    return new Response(JSON.stringify({ results }), { status: 200 });
  }) as typeof fetch;
}

describe("a bulk roster action over 500 people", () => {
  it("revokes 500 at a time and answers as one list", async () => {
    const calls: { url: string; body: Record<string, unknown> }[] = [];
    answer("revoked", calls);
    const { results } = await revokeTrainees("kings", ids(1201));
    assert.deepEqual(calls.map((call) => (call.body.trainee_ids as string[]).length), [500, 500, 201]);
    assert.ok(calls.every((call) => call.url.endsWith("/orgs/kings/trainees/bulk/revoke")));
    assert.equal(results.length, 1201);
  });

  it("moves people to a group, or to no group with null", async () => {
    const calls: { url: string; body: Record<string, unknown> }[] = [];
    answer("updated", calls);
    await setTraineesCohort("kings", ["a", "b"], "c1");
    await setTraineesCohort("kings", ["a"], null);
    assert.deepEqual(calls.map((call) => call.body), [
      { trainee_ids: ["a", "b"], cohort_id: "c1" },
      { trainee_ids: ["a"], cohort_id: null },
    ]);
    assert.ok(calls[0]?.url.endsWith("/trainees/bulk/cohort"));
  });

  it("resends invitations to exactly the ids given", async () => {
    const calls: { url: string; body: Record<string, unknown> }[] = [];
    answer("sent", calls);
    await resendTraineeInvitations("kings", ["a", "b"]);
    assert.deepEqual(calls[0]?.body, { trainee_ids: ["a", "b"] });
    assert.ok(calls[0]?.url.endsWith("/trainees/bulk/resend-invitation"));
  });
});

describe("bulkSummary", () => {
  it("counts the okay outcome and names what else happened", () => {
    const results = [
      { trainee_id: "1", outcome: "sent" },
      { trainee_id: "2", outcome: "sent" },
      { trainee_id: "3", outcome: "already_signed_in" },
      { trainee_id: "4", outcome: "not_found" },
    ];
    assert.equal(
      bulkSummary(results, "sent", "invitations"),
      "Sent 2 of 4 invitations. 1 already signed in. 1 not found.",
    );
  });

  it("says plainly when everything worked", () => {
    const results = [{ trainee_id: "1", outcome: "revoked" }];
    assert.equal(bulkSummary(results, "revoked", "people"), "Revoked 1 of 1 people.");
  });
});

describe("awaitingInvitation", () => {
  const base = {
    id: "t", email: "a@b.com", first_name: "A", last_name: null, cohort_id: null, user_id: "u",
    access_revoked: false, anonymised: false, invitation_pending: false, is_member: true,
    programme_names: [], revision: 1, stations_sat: 0, temporary_password_applied: false,
  } satisfies Trainee;

  it("keeps only rows whose invitation can be resent", () => {
    const pending = { ...base, id: "p", invitation_pending: true };
    const revoked = { ...base, id: "r", invitation_pending: true, access_revoked: true };
    assert.deepEqual(awaitingInvitation([base, pending, revoked]).map((row) => row.id), ["p"]);
  });
});
