import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { heroHeadline, inboxAriaLabel, kindLabel, unreadLabel } from "./model";

describe("inbox model", () => {
  it("caps the pill at 9+", () => {
    assert.equal(unreadLabel(3), "3");
    assert.equal(unreadLabel(9), "9");
    assert.equal(unreadLabel(10), "9+");
  });
  it("writes the hero headline", () => {
    assert.equal(heroHeadline(0), "You're up to date");
    assert.equal(heroHeadline(1), "1 unread message");
    assert.equal(heroHeadline(2), "2 unread messages");
  });
  it("names kinds, with a plain fallback", () => {
    assert.equal(kindLabel("announcement"), "Announcement");
    assert.equal(kindLabel("report_answer"), "Answer to your report");
    assert.equal(kindLabel("whatever"), "Message");
  });
  it("labels the inbox button", () => {
    assert.equal(inboxAriaLabel(0), "Inbox");
    assert.equal(inboxAriaLabel(3), "Inbox, 3 unread");
  });
});
