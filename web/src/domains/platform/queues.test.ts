import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { canReplyInApp, mailtoFor, oldestWaitedLine, openReportsHeadline, waitingHeadline } from "./queues";

describe("queue headlines", () => {
  it("counts open reports", () => {
    assert.equal(openReportsHeadline(0), "No open reports");
    assert.equal(openReportsHeadline(1), "1 open report");
    assert.equal(openReportsHeadline(4), "4 open reports");
  });
  it("says how long the oldest has waited", () => {
    const now = new Date("2026-10-07T12:00:00Z");
    assert.equal(oldestWaitedLine("2026-10-04T12:00:00Z", now), "The oldest has waited 3 days");
    assert.equal(oldestWaitedLine("2026-10-07T09:00:00Z", now), "The oldest has waited 3 hours");
    assert.equal(oldestWaitedLine("2026-10-07T11:50:00Z", now), "The oldest has waited under an hour");
    assert.equal(oldestWaitedLine(null, now), null);
  });
  it("caps the messages count when a page is full", () => {
    assert.equal(waitingHeadline(0, false), "Nothing waiting");
    assert.equal(waitingHeadline(7, false), "7 waiting");
    assert.equal(waitingHeadline(25, true), "More than 25 waiting");
  });
  it("replies in the app only to a sender with an account", () => {
    assert.equal(canReplyInApp({ user_id: "u1" }), true);
    assert.equal(canReplyInApp({ user_id: null }), false);
  });
  it("builds a mailto for anonymous senders", () => {
    assert.equal(mailtoFor({ email: "a@x.com", subject: "Hi there" }), "mailto:a@x.com?subject=Re%3A%20Hi%20there");
    assert.equal(mailtoFor({ email: null }), null);
  });
});
