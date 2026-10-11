import assert from "node:assert/strict";
import { describe, it } from "node:test";
import type { MediaItem } from "@/capabilities/media/api";
import { blogExamTabs, blogsHref, examBlogs } from "@/capabilities/media/blogs";

const blog = (title: string, exam_code: string | null) => ({ title, exam_code }) as MediaItem;

describe("blogs", () => {
  it("offers All, then one tab per exam that has an article", () => {
    const tabs = blogExamTabs([blog("a", "sca"), blog("b", null), blog("c", "plab"), blog("d", "sca")]);
    assert.deepEqual(
      tabs.map((tab) => [tab.label, tab.href]),
      [
        ["All", "/blogs"],
        ["PLAB", "/blogs?exam=plab"],
        ["SCA", "/blogs?exam=sca"],
      ],
    );
  });

  it("links one exam's filter in the query", () => {
    assert.equal(blogsHref("sca"), "/blogs?exam=sca");
    assert.equal(blogsHref(null), "/blogs");
  });

  it("keeps only the exam's own articles, at most the limit", () => {
    const items = [blog("general", null), blog("s1", "sca"), blog("p1", "plab"), blog("s2", "sca"), blog("s3", "sca")];
    assert.deepEqual(
      examBlogs(items, "sca", 2).map((item) => item.title),
      ["s1", "s2"],
    );
  });
});
