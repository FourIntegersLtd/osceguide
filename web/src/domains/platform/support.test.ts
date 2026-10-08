import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  ORG_STATUSES,
  ORG_TYPES,
  STATUS_HELP,
  asContractDate,
  contractDatesError,
  localDay,
  renewalDateError,
  ssoFieldErrors,
  permitsSignIn,
  slugError,
  slugify,
  statusTone,
  attemptStatusTone,
  diagnoseAttempt,
  jobStatusTone,
} from "@/domains/platform/support";

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

  it("offers exactly the types the backend will provision", () => {
    // CreateOrganization.org_type is ^(institution|partner|employer)$.
    assert.deepEqual(
      ORG_TYPES.map((type) => type.value),
      ["institution", "partner", "employer"],
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

  it("refuses what the backend's slug pattern refuses, and accepts what it suggests", () => {
    assert.equal(slugError("Bad Slug!"), "Use only letters, numbers and hyphens, starting with a letter or number.");
    assert.equal(slugError("-acme"), "Use only letters, numbers and hyphens, starting with a letter or number.");
    assert.equal(slugError("a"), "A slug is 2 to 100 characters long.");
    assert.equal(slugError(slugify("Bad Slug!")), null);
    assert.equal(slugError("st-marys"), null);
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
  });
});

describe("contractDatesError", () => {
  const none = { startsAt: "", endsAt: "" };

  it("flags a start after the end, and allows equal, open-ended and blank", () => {
    assert.equal(
      contractDatesError("2027-10-01", "2027-01-01", none),
      "The end date is before the start date",
    );
    assert.equal(contractDatesError("2027-01-01", "2027-01-01", none), null);
    assert.equal(contractDatesError("2027-10-01", "", none), null);
    assert.equal(contractDatesError("", "", none), null);
  });

  it("compares a blank field with the stored date it would leave alone", () => {
    const stored = { startsAt: "2027-01-01", endsAt: "2027-09-30" };
    assert.notEqual(contractDatesError("2028-01-01", "", stored), null);
    assert.notEqual(contractDatesError("", "2026-12-31", stored), null);
    assert.equal(contractDatesError("", "2027-12-31", stored), null);
  });
});

describe("ssoFieldErrors", () => {
  it("names the issuer when enabled without one, and SSO-only without enabled", () => {
    assert.ok(ssoFieldErrors({ issuer: " ", enabled: true, sso_only: false }).issuer);
    assert.ok(ssoFieldErrors({ issuer: "https://x", enabled: false, sso_only: true }).sso_only);
    assert.deepEqual(ssoFieldErrors({ issuer: "", enabled: false, sso_only: false }), {});
    assert.deepEqual(ssoFieldErrors({ issuer: "https://x", enabled: true, sso_only: true }), {});
  });
});

describe("renewalDateError", () => {
  it("refuses an end date that is today or earlier", () => {
    const refused = "A renewal must end in the future";
    assert.equal(renewalDateError("2026-10-07", "2026-10-08"), refused);
    assert.equal(renewalDateError("2026-10-08", "2026-10-08"), refused);
    assert.equal(renewalDateError("2026-10-09", "2026-10-08"), null);
    assert.equal(renewalDateError("", "2026-10-08"), null);
  });

  it("reads today in local time", () => {
    assert.equal(localDay(new Date(2026, 9, 8, 23, 30)), "2026-10-08");
  });
});
