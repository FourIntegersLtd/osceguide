import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  bandFor,
  bandLegend,
  bandName,
  formatAggregate,
  ratingFraction,
  ratingLabel,
  ratingTone,
  readDisplay,
  toneVariant,
} from "@/capabilities/feedback/rubric";
import { CASC_DISPLAY, ORTHO_DISPLAY, SCA_DISPLAY, SCA_RATING } from "@/capabilities/feedback/testRubrics";

describe("one rating", () => {
  it("reads a scale by position, as the backend's rating_fraction does", () => {
    assert.deepEqual(
      ["G", "A", "R", "X"].map((value) => ratingFraction(SCA_RATING, value)),
      [1, 0.66, 0.33, null],
    );
  });

  it("uses the tone pinned to a scale letter", () => {
    const display = readDisplay(SCA_DISPLAY);
    assert.deepEqual(
      ["G", "A", "R"].map((value) => ratingTone(SCA_RATING, display, value)),
      ["good", "fair", "poor"],
    );
  });

  it("writes each kind its own way", () => {
    const range = { kind: "range", field: "score", minimum: 0, maximum: 10, step: "integer" };
    const boolean = { kind: "boolean", field: "competent", step: "number" };
    assert.equal(ratingLabel(range, 7), "7/10");
    assert.equal(ratingLabel(SCA_RATING, "A"), "Amber");
    assert.equal(ratingLabel(boolean, true), "Met");
    assert.equal(ratingLabel(boolean, false), "Not met");
    assert.equal(ratingLabel(SCA_RATING, null), "Not rated");
  });
});

describe("totals and bands", () => {
  it("writes sums against their maximum and shares as a percentage", () => {
    assert.equal(formatAggregate("sum", 0.6000000000000001, 4), "0.6/4");
    assert.equal(formatAggregate("mean", 3.6, 10), "3.6/10");
    assert.equal(formatAggregate("percentAchieved", 66.67, 100), "67%");
    assert.equal(formatAggregate("sum", null, 12), "Not scored");
  });

  it("puts an Ortho total in its band, edges included", () => {
    const display = readDisplay(ORTHO_DISPLAY);
    assert.deepEqual(bandLegend(display), ["0–17 Poor", "18–34 Fair", "35–42 Good", "43–50 Excellent"]);
    assert.deepEqual(
      [0, 17, 18, 34, 35, 42, 43, 50].map((total) => {
        const band = bandFor(display, total);
        return band ? bandName(band) : null;
      }),
      ["Poor", "Poor", "Fair", "Fair", "Good", "Good", "Excellent", "Excellent"],
    );
  });

  it("has no band when the display sets none", () => {
    assert.equal(bandFor(readDisplay(CASC_DISPLAY), 20), null);
  });

  it("maps author tones onto four badge colours, unknown ones neutral", () => {
    assert.deepEqual(
      ["excellent", "good", "fair", "weak", "poor", "amber", null].map(toneVariant),
      ["success", "success", "warning", "danger", "danger", "neutral", "neutral"],
    );
  });
});
