import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { studyItemHref } from "@/capabilities/media/studyPaths";

const hrefFor = (path: string) => `/app/me${path}`;

describe("studyItemHref", () => {
  it("opens an article on the public blogs page, outside the workspace", () => {
    assert.equal(studyItemHref(hrefFor, "blog", "a-day-in-sca"), "/blogs/a-day-in-sca");
  });

  it("opens every other kind inside the workspace", () => {
    assert.equal(studyItemHref(hrefFor, "summary", "asthma"), "/app/me/summary/asthma");
    assert.equal(studyItemHref(hrefFor, "slide_deck", "asthma"), "/app/me/slides?deck=asthma");
  });
});
