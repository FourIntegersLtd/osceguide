import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { VISIBLE_EXAM_ITEMS } from "@/domains/marketing/landingCopy";
import { FOOTER_COMPANY, FOOTER_EXAMS, FOOTER_PRODUCT, LANDING_NAV_LINKS, SITE_NAV_LINKS } from "@/domains/marketing/site/siteLinks";
import { EXAM_CONFIGS, VISIBLE_EXAMS } from "@/domains/marketing/pricingContent";

describe("the exams offered on the landing", () => {
  it("shows SCA and PLAB 2 on the exam cards", () => {
    assert.deepEqual(VISIBLE_EXAM_ITEMS.map((exam) => exam.code), ["SCA", "PLAB 2"]);
  });

  it("shows SCA and PLAB 2 on the pricing tabs", () => {
    assert.deepEqual(VISIBLE_EXAMS.map((key) => EXAM_CONFIGS[key].name), ["SCA", "PLAB 2"]);
  });
});

describe("hidden exams are linked from nowhere", () => {
  it("keeps CASC and ST3 out of the footer, nav and exam cards", () => {
    const hrefs = [...FOOTER_EXAMS, ...SITE_NAV_LINKS, ...FOOTER_PRODUCT, ...FOOTER_COMPANY, ...LANDING_NAV_LINKS, ...VISIBLE_EXAM_ITEMS].map((l) => l.href);
    assert.deepEqual(hrefs.filter((href) => /casc|st3|ortho/i.test(href)), []);
    assert.deepEqual(FOOTER_EXAMS.map((l) => l.href), ["/exams/sca", "/exams/plab"]);
  });
});
