import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { EXAM_CONFIGS, configFor, formatScore, formatTick } from "@/domains/train/dashboard/examConfig";
import { aboutFor } from "@/domains/train/dashboard/aboutCopy";

describe("exam configuration", () => {
  it("keeps each exam's own scale, which is what the four screens differed by", () => {
    assert.equal(configFor("plab").domains.maxScore, 4);
    assert.equal(configFor("plab").trend.threshold, 7);
    assert.equal(configFor("casc").domains.threshold, 0.8);
    assert.equal(configFor("ortho").trend.maxScore, 50);
    assert.equal(configFor("ortho").domains.layout, "vertical");
  });

  it("gives an unknown exam a dashboard rather than a crash", () => {
    const config = configFor("mrcp");
    assert.equal(config.code, "mrcp");
    assert.equal(config.label, "MRCP");
    // No invented threshold: nothing is known about how this exam is marked.
    assert.equal(config.domains.threshold, undefined);
  });

  it("switches SCA's extra sections on by configuration, not by component", () => {
    assert.deepEqual(configFor("sca").sections, {
      hero: true,
      weeklyTrend: true,
      insights: true,
      firstStation: false,
    });
    for (const code of ["plab", "casc", "ortho"]) {
      assert.equal(configFor(code).sections.hero, false, `${code} has no hero`);
    }
  });

  it("writes a score the way its exam does", () => {
    assert.equal(formatScore(configFor("plab").domains, 2.5), "2.50 / 4");
    assert.equal(formatScore(configFor("plab").trend, 7), "7.0 / 12");
    assert.equal(formatScore(configFor("casc").domains, 0.815), "81.5%");
    assert.equal(formatScore(configFor("casc").trend, 80), "80.0%");
    assert.equal(formatScore(configFor("ortho").trend, 35), "35 / 50");
    assert.equal(formatTick(configFor("casc").domains, 0.8), "80%");
    assert.equal(formatTick(configFor("plab").domains, 2), "2");
  });

  it("has all three about modals, and a swatch colour behind every swatch", () => {
    for (const [code, config] of Object.entries(EXAM_CONFIGS)) {
      const about = aboutFor(code);
      for (const key of ["summary", "domain", "trend"] as const) {
        assert.ok(about[key].items.length > 0, `${code} ${key} has items`);
        for (const item of about[key].items) {
          if (item.marker !== "swatch") continue;
          const domain = item.swatchFor ?? item.title;
          assert.ok(
            config.domains.colors?.[domain],
            `${code} names a colour for ${domain}`,
          );
        }
      }
    }
  });
});
