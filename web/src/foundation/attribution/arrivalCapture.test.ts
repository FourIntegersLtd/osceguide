import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { toArrivalPayload } from "@/foundation/attribution/arrivalCapture";
import { parseReferralParams } from "@/foundation/attribution/parseReferralParams";
import type { ParsedReferralParams } from "@/foundation/attribution/partnerTypes";

/**
 * What a partner is billed on.
 *
 * The arriving URL and the ledger row are two different shapes, and the whole
 * of the money is in the mapping between them: a partner name that is not the
 * one in `utm_source`, or a `ref_id` dropped on the way, and the partner's
 * arrivals still look fine in the product while counting for nobody.
 */
describe("arrival payload", () => {
  it("carries the partner, the reference and the landing URL the visitor actually saw", () => {
    const parsed: ParsedReferralParams = {
      partner: "bmj",
      exam: "sca",
      utmMedium: "email",
      utmCampaign: "aug-recruit",
      refId: "bmj-sca",
      landingPath: "/exams/sca?utm_source=bmj&utm_medium=email&ref_id=bmj-sca",
    };
    assert.deepEqual(toArrivalPayload(parsed, "visitor-1"), {
      partner: "bmj",
      visitor_key: "visitor-1",
      ref_id: "bmj-sca",
      landing_path: "/exams/sca?utm_source=bmj&utm_medium=email&ref_id=bmj-sca",
      utm: { source: "bmj", medium: "email", campaign: "aug-recruit" },
    });
  });

  it("omits the utm parts that were not in the link rather than sending empty strings", () => {
    // An empty `utm_medium` reads as "a campaign that set medium to nothing" in
    // the funnel, which is a different statement from "this link had no medium".
    const parsed: ParsedReferralParams = {
      partner: "bmj",
      exam: "plab",
      utmMedium: null,
      utmCampaign: null,
      refId: null,
      landingPath: "/exams/plab?utm_source=bmj",
    };
    assert.deepEqual(toArrivalPayload(parsed, "v").utm, { source: "bmj" });
    assert.equal(toArrivalPayload(parsed, "v").ref_id, null);
  });

  it("round-trips a real referral URL into a payload the backend will accept", () => {
    const parsed = parseReferralParams({
      host: "www.osceguide.com",
      pathname: "/exams/ortho",
      search: "?utm_source=bmj&utm_medium=social&ref_id=bmj-ortho",
    });
    assert.ok(parsed, "the parser should recognise a pilot partner on an exam landing");
    const payload = toArrivalPayload(parsed!, "0f0f0f0f-0f0f-0f0f-0f0f-0f0f0f0f0f0f");
    // Mirrors `RecordArrival`: partner and key are the only required fields, and
    // both are length-bounded server-side.
    assert.equal(payload.partner, "bmj");
    assert.equal(payload.visitor_key.length <= 64, true);
    assert.equal(payload.ref_id, "bmj-ortho");
    assert.match(payload.landing_path, /^\/exams\/ortho\?/);
  });

  it("records nothing for a link that is not a partner's", () => {
    // Unknown utm_source, and a known partner with no exam context — the pilot
    // is per-exam, so an unattributable visit must not land in a partner's
    // funnel at all.
    assert.equal(
      parseReferralParams({ host: "www.osceguide.com", pathname: "/", search: "?utm_source=nobody" }),
      null,
    );
    assert.equal(
      parseReferralParams({ host: "www.osceguide.com", pathname: "/", search: "?utm_source=bmj" }),
      null,
    );
  });
});
