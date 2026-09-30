import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { getDashboardCopy } from "@/foundation/attribution/copy";
import {
  dateRangeForPreset,
  detectRangePreset,
  formatActiveFilterSummary,
  validateCustomRange,
} from "@/foundation/attribution/presets";
import { filterScope, parseAttributionTab, tabsForMode } from "@/foundation/attribution/tabs";
import {
  bucketForRange,
  campaignLabel,
  funnelCounts,
  funnelDonutSlices,
  partnerDisplayName,
  partnerHeroFigures,
  signedUpPercent,
  visibleDefinitions,
} from "@/foundation/attribution/viewModel";

const NOW = new Date("2026-09-30T10:00:00Z");

describe("date ranges", () => {
  it("builds each preset from today in UTC", () => {
    assert.deepEqual(dateRangeForPreset("this_month", NOW), { fromDate: "2026-09-01", toDate: "2026-09-30" });
    assert.deepEqual(dateRangeForPreset("last_month", NOW), { fromDate: "2026-08-01", toDate: "2026-08-31" });
    assert.deepEqual(dateRangeForPreset("3m", NOW), { fromDate: "2026-06-30", toDate: "2026-09-30" });
  });

  it("names the preset a range matches, else custom", () => {
    assert.equal(detectRangePreset("2026-08-01", "2026-08-31", NOW), "last_month");
    assert.equal(detectRangePreset("2026-08-02", "2026-08-31", NOW), "custom");
  });

  it("refuses bad custom ranges with the legacy words", () => {
    assert.equal(validateCustomRange("", "2026-09-01", NOW), "Choose both a start and an end date.");
    assert.equal(validateCustomRange("2026-09-02", "2026-09-01", NOW), "The start date must be on or before the end date.");
    assert.equal(validateCustomRange("2026-09-01", "2026-10-01", NOW), "The end date can't be in the future.");
    assert.equal(validateCustomRange("2025-12-31", "2026-09-01", NOW), "There's no data before 2026-01-01; the pilot started this year.");
    assert.equal(validateCustomRange("2026-09-01", "2026-09-30", NOW), null);
  });

  it("summarises the active filters", () => {
    const filters = { fromDate: "2026-09-01", toDate: "2026-09-30", partner: "bmj", exam: "sca", utmCampaign: "" };
    assert.equal(formatActiveFilterSummary(filters, "internal"), "BMJ · SCA · 1 Sept 2026 – 30 Sept 2026");
    assert.equal(formatActiveFilterSummary({ ...filters, exam: "" }, "partner"), "All exams · 1 Sept 2026 – 30 Sept 2026");
  });

  it("picks the chart bucket from the range length", () => {
    assert.equal(bucketForRange("2026-09-01", "2026-09-30"), "day");
    assert.equal(bucketForRange("2026-06-01", "2026-09-30"), "week");
    assert.equal(bucketForRange("2026-01-01", "2026-09-30"), "month");
  });
});

describe("tabs", () => {
  it("gives admin five tabs and a partner four, in order", () => {
    assert.deepEqual(tabsForMode("internal").map((tab) => tab.label), [
      "Overview", "Revenue", "Recent activity", "How we count", "Access",
    ]);
    assert.deepEqual(tabsForMode("partner").map((tab) => tab.label), [
      "Overview", "Performance", "Your fee", "How we count",
    ]);
  });

  it("never lets a partner reach Revenue or Access", () => {
    assert.equal(parseAttributionTab("revenue", "partner"), "overview");
    assert.equal(parseAttributionTab("access", "partner"), "overview");
    assert.equal(parseAttributionTab("fee", "partner"), "fee");
  });

  it("keeps only the partner picker on the Access tab", () => {
    assert.equal(filterScope("access", "internal"), "partner-only");
    assert.equal(filterScope("revenue", "internal"), "full");
  });
});

describe("funnel figures", () => {
  it("takes the funnel's counts over the summary's, keeping an untracked step null", () => {
    const funnel = {
      steps: [
        { step: "landing", event: "x", count: 200 },
        { step: "signup", event: "y", count: 50 },
        { step: "purchase", event: "z", count: null },
      ],
    } as Parameters<typeof funnelCounts>[0];
    assert.deepEqual(funnelCounts(funnel, { visits: 1, signups: 1, paid: 1 }), {
      landing: 200, signup: 50, purchase: null,
    });
    assert.deepEqual(funnelCounts(null, { visits: 9, signups: 3, paid: 1 }), { landing: 9, signup: 3, purchase: 1 });
  });

  it("splits the ring so it sums to the visits, and reports the signed-up share", () => {
    const counts = { landing: 100, signup: 40, purchase: 10 };
    assert.deepEqual(funnelDonutSlices(counts).map((slice) => [slice.name, slice.value]), [
      ["Visited", 60], ["Signed up", 30], ["Paid", 10],
    ]);
    assert.equal(signedUpPercent(counts), 40);
    assert.equal(signedUpPercent({ landing: 0, signup: 0, purchase: 0 }), 0);
  });
});

describe("what a partner may see", () => {
  it("has no revenue, margin or spend in the hero figures", () => {
    const figures = partnerHeroFigures({
      raw_arrival_count: 10, unique_arrival_count: 8, acquired_user_count: 3, paying_user_count: 1,
      fee: { estimated_spend_pence: 400 },
    } as Parameters<typeof partnerHeroFigures>[0]);
    assert.deepEqual(figures, { visits: 10, unique: 8, signups: 3, paid: 1, feePence: 400 });
  });

  it("drops every admin-only definition from the partner's How we count", () => {
    const all = getDashboardCopy("internal").methodology.definitions;
    const shown = visibleDefinitions("partner", all);
    assert.equal(shown.some((entry) => entry.internalOnly), false);
    assert.equal(visibleDefinitions("internal", all).length, all.length);
  });
});

describe("labels", () => {
  it("shows an empty or unknown campaign as a dash", () => {
    assert.equal(campaignLabel("unknown"), "—");
    assert.equal(campaignLabel(null), "—");
    assert.equal(campaignLabel("spring"), "spring");
  });

  it("names the partner in prose", () => {
    assert.equal(partnerDisplayName("bmj"), "BMJ On Exam");
  });
});
