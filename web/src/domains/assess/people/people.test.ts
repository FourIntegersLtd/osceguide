import assert from "node:assert/strict";
import { afterEach, describe, it } from "node:test";
import type { Membership } from "@/domains/assess/team/api";
import { revokeMemberships } from "@/domains/assess/team/api";
import {
  LAST_ADMIN_MESSAGE,
  ROLE_CHOICE_HELP,
  bulkRevokeFailure,
  isAwaitingInvite,
  resendSummary,
  revokableStaff,
  revokeLead,
  staffRevokeTitle,
} from "@/domains/assess/team/support";
import { PlatformError } from "@/foundation/platform-client";
import {
  ADD_TO_GROUP_LABEL,
  MOVE_TO_YEAR_GROUP_LABEL,
  NO_YEAR_GROUP_LABEL,
  addToGroupIds,
  addToGroupSummary,
  cohortDeleteLead,
} from "@/domains/assess/roster/support";
import { INSTITUTION_WORDS } from "@/domains/assess/vocabulary";
import { initialPeopleTab, peopleTabs } from "@/domains/assess/people/support";

const realFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = realFetch;
});

function member(partial: Partial<Membership> & { id: string; role: string }): Membership {
  return {
    user_id: `u-${partial.id}`,
    email: `${partial.id}@stmarys.ac.uk`,
    status: "active",
    revoked_at: null,
    invited: false,
    circuits_led: 0,
    ...partial,
  } as unknown as Membership;
}

describe("the People tabs", () => {
  const trainees = { id: "trainees", label: "Trainees" };

  it("shows an org admin every tab, in the order of the board", () => {
    const tabs = peopleTabs({ manageTeam: true }, INSTITUTION_WORDS);
    assert.deepEqual(
      tabs.map((tab) => [tab.key, tab.label]),
      [
        ["trainees", "Trainees"],
        ["staff", "Staff"],
        ["groups", "Groups and year groups"],
        ["access", "Exam access"],
        ["history", "History"],
      ],
    );
    assert.equal(tabs[0]?.label, trainees.label);
  });

  it("shows a supervisor the trainees and groups only, read only", () => {
    assert.deepEqual(
      peopleTabs({ manageTeam: false }, INSTITUTION_WORDS).map((tab) => tab.key),
      ["trainees", "groups"],
    );
  });

  it("opens /team on the Staff tab and /trainees on Trainees", () => {
    assert.equal(initialPeopleTab("team"), "staff");
    assert.equal(initialPeopleTab("trainees"), "trainees");
  });
});

describe("the trainee bulk bar words", () => {
  it("says year group where it moves a cohort, and has its own group action", () => {
    assert.equal(MOVE_TO_YEAR_GROUP_LABEL, "Move to year group…");
    assert.equal(NO_YEAR_GROUP_LABEL, "No year group");
    assert.equal(ADD_TO_GROUP_LABEL, "Add to group…");
  });

  it("adds people to a group without dropping who is already in it", () => {
    assert.deepEqual(addToGroupIds(["a", "b"], ["b", "c"]), ["a", "b", "c"]);
  });

  it("calls a cohort a year group when deleting it", () => {
    assert.match(
      cohortDeleteLead("Year 4", 2),
      /^Delete “Year 4”\? Nobody can be put into it afterwards\. This cannot be undone, and a year group that still has trainees in it is not deleted\. The 2 sittings held for it are kept but no longer belong to any year group\.$/,
    );
  });
});

describe("add to group", () => {
  it("reports only who is really in the group afterwards", () => {
    assert.equal(addToGroupSummary(["a", "b"], ["a", "b", "z"]), "Added 2 of 2 people to the group.");
    assert.equal(
      addToGroupSummary(["a", "b", "c"], ["a"]),
      "Added 1 of 3 people to the group. 2 are not in it: the group changed while you were adding. Try again.",
    );
  });
});

describe("staff bulk revoke", () => {
  it("posts the ticked ids to memberships/bulk/revoke", async () => {
    const calls: { url: string; body: unknown }[] = [];
    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      calls.push({ url: String(input), body: JSON.parse(String(init?.body)) });
      return new Response(
        JSON.stringify({ results: [{ membership_id: "m1", outcome: "revoked" }] }),
        { status: 200 },
      );
    }) as typeof fetch;
    const { results } = await revokeMemberships("kings", ["m1"]);
    assert.equal(calls.length, 1);
    assert.ok(calls[0]?.url.endsWith("/orgs/kings/memberships/bulk/revoke"));
    assert.deepEqual(calls[0]?.body, { membership_ids: ["m1"] });
    assert.equal(results[0]?.outcome, "revoked");
  });

  it("leaves out the owner, revoked rows and you", () => {
    const rows = [
      member({ id: "o", role: "owner" }),
      member({ id: "p", role: "supervisor" }),
      member({ id: "me", role: "supervisor" }),
      member({ id: "r", role: "supervisor", status: "revoked", revoked_at: "2026-11-01T00:00:00Z" }),
    ];
    assert.deepEqual(revokableStaff(rows, rows, "u-me").map((row) => row.id), ["p"]);
  });

  it("leaves out the last admin standing, but not an admin when another stays", () => {
    const sole = [member({ id: "a", role: "admin" }), member({ id: "s", role: "supervisor" })];
    assert.deepEqual(revokableStaff(sole, sole, "u-x").map((row) => row.id), ["s"]);
    const two = [member({ id: "a", role: "admin" }), member({ id: "b", role: "admin" })];
    assert.deepEqual(revokableStaff([two[0]!], two, "u-x").map((row) => row.id), ["a"]);
    assert.deepEqual(revokableStaff(two, two, "u-x"), []);
  });

  it("tells a refused batch (409 last_admin) apart from any other failure", () => {
    const refused = new PlatformError(409, { code: "last_admin", message: "x" });
    assert.equal(bulkRevokeFailure(refused, "fallback"), LAST_ADMIN_MESSAGE);
    assert.match(LAST_ADMIN_MESSAGE, /nobody was revoked/);
    assert.equal(bulkRevokeFailure(new Error("boom"), "fallback"), "fallback");
  });

  it("offers a resend only to someone invited, active and not the owner", () => {
    assert.equal(isAwaitingInvite(member({ id: "i", role: "supervisor", invited: true })), true);
    assert.equal(isAwaitingInvite(member({ id: "j", role: "supervisor" })), false);
    assert.equal(isAwaitingInvite(member({ id: "k", role: "owner", invited: true })), false);
    assert.equal(resendSummary([{ outcome: "sent" }, { outcome: "skipped" }]), "Resent 1 of 2 invitations.");
  });

  it("titles the confirmation by count", () => {
    assert.equal(staffRevokeTitle(1), "Revoke access for 1 staff member?");
    assert.equal(staffRevokeTitle(3), "Revoke access for 3 staff members?");
  });

  it("explains the two roles together in the change-role box", () => {
    assert.equal(
      ROLE_CHOICE_HELP,
      "Supervisor: runs circuits and marks the candidates on them. Admin: also manages the team and the organisation's settings, and signs off results.",
    );
  });
});

describe("revokeLead", () => {
  it("warns when you revoke yourself and names anyone else", () => {
    assert.match(revokeLead("me@x.org", true), /your own access/);
    assert.match(revokeLead("a@x.org", false), /^a@x\.org will lose access/);
  });
});
