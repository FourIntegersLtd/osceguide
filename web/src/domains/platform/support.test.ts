import assert from "node:assert/strict";
import { describe, it } from "node:test";
import type { Organization } from "@/domains/platform/api";
import {
  ORG_STATUSES,
  ORG_TYPES,
  STATUS_HELP,
  asContractDate,
  matchesSearch,
  permitsSignIn,
  slugify,
  statusTone,
  attemptStatusTone,
  diagnoseAttempt,
  formatMoney,
  jobStatusTone,
} from "@/domains/platform/support";

const org = (over: Partial<Organization> = {}): Organization => ({
  id: "11111111-1111-1111-1111-111111111111",
  slug: "kings",
  name: "King's College",
  org_type: "institution",
  status: "active",
  require_staff_mfa: false,
  created_at: "2026-01-04T09:00:00Z",
  ...over,
});

describe("staff console vocabulary", () => {
  it("agrees with the backend about who may sign in", () => {
    // ACTIVE_ORG_STATUSES in tenancy/domain.py. A status added to the list
    // above without being added there reads as access it does not grant.
    assert.deepEqual(ORG_STATUSES.filter(permitsSignIn), ["trial", "active"]);
  });

  it("explains every status it offers", () => {
    // A select whose help text is missing for one option is how "churned" and
    // "inactive" came to be chosen interchangeably in the old console.
    for (const status of ORG_STATUSES) {
      assert.ok(STATUS_HELP[status], `${status} has no help text`);
    }
  });

  it("offers only the two types the backend will provision", () => {
    // CreateOrganization.org_type is ^(institution|partner)$. An employer is
    // an institution running exam-mode sittings, not a third kind.
    assert.deepEqual(
      ORG_TYPES.map((type) => type.value),
      ["institution", "partner"],
    );
  });

  it("gives a suspended tenant no reassuring colour", () => {
    assert.equal(statusTone("active"), "success");
    assert.equal(statusTone("trial"), "warning");
    assert.equal(statusTone("suspended"), "neutral");
    assert.equal(statusTone("churned"), "neutral");
  });
});

describe("slugify", () => {
  it("makes a URL segment out of a display name", () => {
    assert.equal(slugify("King's College London"), "king-s-college-london");
    assert.equal(slugify("  BMJ  "), "bmj");
  });

  it("leaves no leading or trailing separator", () => {
    // The backend's pattern is ^[a-zA-Z0-9][a-zA-Z0-9-]*$, so a name starting
    // with punctuation would otherwise produce a slug it refuses.
    assert.equal(slugify("—Acme—"), "acme");
  });
});

describe("matchesSearch", () => {
  it("matches the name and the slug, ignoring case", () => {
    assert.ok(matchesSearch(org(), "king"));
    assert.ok(matchesSearch(org(), "KINGS"));
    assert.ok(!matchesSearch(org(), "bmj"));
  });

  it("matches everything when nothing has been typed", () => {
    assert.ok(matchesSearch(org(), ""));
    assert.ok(matchesSearch(org(), "   "));
  });
});

describe("asContractDate", () => {
  it("sends midnight UTC, so a contract ends at the start of its last day", () => {
    assert.equal(asContractDate("2026-09-19"), "2026-09-19T00:00:00Z");
  });

  it("distinguishes clearing a date from leaving it alone", () => {
    // null clears it; the caller omits the key entirely to leave it alone.
    assert.equal(asContractDate(""), null);
    assert.equal(asContractDate("   "), null);
  });
});


describe("the support view's diagnosis", () => {
  const base = { transcript_complete: true, result_policy_versions: [] as string[], scoring_job: null };
  it("names each cause of missing feedback with the fix", () => {
    assert.equal(diagnoseAttempt({ ...base, status: "running", chunk_count: 3 })?.action, "salvage");
    assert.equal(diagnoseAttempt({ ...base, status: "running", chunk_count: 0 })?.action, "fail");
    assert.equal(diagnoseAttempt({ ...base, status: "interaction_complete" })?.action, "rescore");
    assert.equal(
      diagnoseAttempt({ ...base, status: "interaction_complete", scoring_job: { status: "failed" } })?.action,
      "rescore",
    );
  });
  it("says nothing is wrong when the marking is done or on its way", () => {
    assert.equal(diagnoseAttempt({ ...base, status: "evaluated" }), null);
    assert.equal(diagnoseAttempt({ ...base, status: "interaction_complete", scoring_job: { status: "todo" } }), null);
    assert.equal(diagnoseAttempt({ ...base, status: "interaction_complete", result_policy_versions: ["v1"] }), null);
  });
  it("colours what needs acting on", () => {
    assert.equal(attemptStatusTone("failed"), "danger");
    assert.equal(jobStatusTone("failed"), "danger");
    assert.equal(jobStatusTone("succeeded"), "success");
    assert.equal(formatMoney(2499, "gbp"), "£24.99");
  });
});
