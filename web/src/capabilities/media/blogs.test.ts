import assert from "node:assert/strict";
import { describe, it } from "node:test";
import type { MediaItem } from "@/capabilities/media/api";
import { BLOG_EXAM_TABS, articleBlurb, blogsHref } from "@/capabilities/media/blogs";

const item = (summary: string | null, body_md?: string) => ({ summary, content: body_md ? { body_md } : null }) as MediaItem;

describe("blogs", () => {
  it("offers All, then one tab per exam the platform runs", () => {
    assert.deepEqual(
      BLOG_EXAM_TABS.map((tab) => [tab.code, tab.label]),
      [
        [null, "All"],
        ["sca", "SCA"],
        ["plab", "PLAB"],
        ["casc", "CASC"],
        ["ortho", "ORTHO"],
      ],
    );
  });

  it("links one exam's filter in the query", () => {
    assert.equal(blogsHref("sca"), "/blogs?exam=sca");
    assert.equal(blogsHref(null), "/blogs");
  });

  it("blurbs an article with its summary, else the start of its body, else nothing", () => {
    assert.equal(articleBlurb(item(" A summary ", "Body text."), 50), "A summary");
    assert.equal(articleBlurb(item(null, "## Head\n\nBody text."), 50), "Head Body text.");
    assert.equal(articleBlurb(item(null), 50), "");
  });
});
