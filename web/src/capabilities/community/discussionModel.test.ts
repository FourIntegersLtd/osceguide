import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  ASSISTANT_LABEL,
  COMMUNITY_TABS,
  authorLabel,
  listFilterFor,
  parseTab,
  sortReplies,
  tabHref,
} from "@/capabilities/community/discussionModel";

describe("community tabs", () => {
  it("offers All, Exam, My questions, My answers in that order", () => {
    assert.deepEqual(
      COMMUNITY_TABS.map((tab) => tab.label),
      ["All", "Exam", "My questions", "My answers"],
    );
  });

  it("reads the tab from the URL and falls back to All", () => {
    assert.equal(parseTab("exam"), "exam");
    assert.equal(parseTab("questions"), "questions");
    assert.equal(parseTab("answers"), "answers");
    assert.equal(parseTab("bogus"), "all");
    assert.equal(parseTab(null), "all");
  });

  it("builds the tab link and the composer link", () => {
    assert.equal(tabHref("exam"), "?tab=exam");
    assert.equal(tabHref("all", { compose: true }), "?tab=all&compose=1");
  });
});

describe("sortReplies", () => {
  const replies = [
    { id: "b", created_at: "2026-10-02T10:00:00Z" },
    { id: "a", created_at: "2026-10-01T10:00:00Z" },
    { id: "c", created_at: "2026-10-03T10:00:00Z" },
  ];

  it("puts the newest first", () => {
    assert.deepEqual(sortReplies(replies, "newest").map((r) => r.id), ["c", "b", "a"]);
  });

  it("puts the oldest first", () => {
    assert.deepEqual(sortReplies(replies, "oldest").map((r) => r.id), ["a", "b", "c"]);
  });

  it("leaves the input untouched", () => {
    sortReplies(replies, "newest");
    assert.deepEqual(replies.map((r) => r.id), ["b", "a", "c"]);
  });
});

describe("listFilterFor", () => {
  it("filters the Exam tab by the current exam only, whatever the category, and no other tab", () => {
    assert.deepEqual(listFilterFor("exam", "sca"), { examCode: "sca" });
    assert.deepEqual(listFilterFor("all", "sca"), {});
  });

  it("has no filter for the Exam tab when there is no current exam, so it never widens to every question", () => {
    assert.equal(listFilterFor("exam", null), null);
  });
});

describe("authorLabel", () => {
  const person = { author_id: "a1", author_name: "Ada", is_assistant: false };

  it("says Athena wrote an assistant reply", () => {
    assert.equal(ASSISTANT_LABEL, "Athena");
    assert.equal(authorLabel({ author_id: null, author_name: null, is_assistant: true }, "a1", "Ada"), "Athena");
  });

  it("keeps the viewer, a named author and a deleted account as before", () => {
    assert.equal(authorLabel(person, "a1", "Ada L"), "@Ada L");
    assert.equal(authorLabel(person, "b2", "Bo"), "@Ada");
    assert.equal(authorLabel({ ...person, author_name: null }, "b2", "Bo"), "@a colleague");
  });
});
