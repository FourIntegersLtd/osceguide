import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  ACCESS_FILTERS,
  USER_STATUSES,
  accessOf,
  accessTone,
  directoryListingTotal,
  groupTitle,
  planLabel,
  userStatusTone,
} from "@/domains/platform/users/vocabulary";

describe("the directory's access states", () => {
  it("offers exactly the backend's three facets, in the old modal's order", () => {
    // `ACCESS_PATTERN` in dashboard/router_platform.py.
    assert.deepEqual(
      ACCESS_FILTERS.map((entry) => entry.value),
      ["paid", "trial", "not_started"],
    );
  });

  it("puts a row in the group its filter would find it in", () => {
    assert.equal(accessOf({ has_paid: true, attempt_count: 0 }), "paid");
    assert.equal(accessOf({ has_paid: true, attempt_count: 9 }), "paid");
    assert.equal(accessOf({ has_paid: false, attempt_count: 1 }), "trial");
    assert.equal(accessOf({ has_paid: false, attempt_count: 0 }), "not_started");
  });

  it("gives an unpaid trialist an amber, not a green", () => {
    assert.equal(accessTone("paid"), "success");
    assert.equal(accessTone("trial"), "warning");
    assert.equal(accessTone("not_started"), "neutral");
  });

  it("offers the two statuses the backend accepts", () => {
    // `UpdatePlatformUser.status` is ^(active|deactivated)$.
    assert.deepEqual(
      USER_STATUSES.map((entry) => entry.value),
      ["active", "deactivated"],
    );
    assert.equal(userStatusTone("deactivated"), "danger");
    assert.equal(userStatusTone("active"), "success");
  });
});

describe("planLabel", () => {
  it("reads the plan code rather than knowing the list", () => {
    assert.equal(planLabel("one_month"), "1 month");
    assert.equal(planLabel("three_month"), "3 months");
    assert.equal(planLabel("six_month"), "6 months");
    assert.equal(planLabel("12_month"), "12 months");
  });

  it("prints an unfamiliar code readably and an absent one as no plan", () => {
    assert.equal(planLabel("bmj_pilot"), "bmj pilot");
    assert.equal(planLabel(null), "No plan");
    assert.equal(planLabel(""), "No plan");
  });
});

describe("groupTitle", () => {
  it("prefers the exam's name and falls back to the code", () => {
    assert.equal(groupTitle("sca", "MRCGP SCA", 412), "MRCGP SCA · 412");
    assert.equal(groupTitle("sca", "  ", 3), "SCA · 3");
  });
});

describe("directoryListingTotal", () => {
  const summary = {
    total: 1000,
    paid: 436,
    trial: 302,
    unassigned: 50,
    unassigned_paid: 36,
    unassigned_trial: 2,
    exams: [
      { code: "sca", name: "SCA", users: 923, paid: 400, trial: 300, not_started: 223 },
    ],
  };

  it("uses the exam headcount when only the exam facet is set", () => {
    assert.equal(directoryListingTotal(summary, { examCode: "sca" }), 923);
  });

  it("uses the access facet when that filter is on", () => {
    assert.equal(
      directoryListingTotal(summary, { examCode: "sca", access: "paid" }),
      400,
    );
  });

  it("counts payers across the whole directory as the Paid tile does, exam or none", () => {
    assert.equal(directoryListingTotal(summary, { access: "paid" }), 436);
    assert.equal(directoryListingTotal(summary, { access: "trial" }), 302);
    assert.equal(directoryListingTotal(summary, { unassigned: true, access: "paid" }), 36);
  });

  it("returns nothing when a search would change the count", () => {
    assert.equal(directoryListingTotal(summary, { examCode: "sca", q: "ann" }), undefined);
  });
});
