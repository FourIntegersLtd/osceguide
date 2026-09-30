import assert from "node:assert/strict";
import { it } from "node:test";
import type { QueueStatus } from "../api";
import { latestQueueStatus } from "./queueState";
const waiting: QueueStatus = { entry_id: "queue-1", status: "waiting", waiting_count: 1, audience: { visibility: "public", org_id: null, group_id: null } };
it("ignores retained SSE matches from an earlier queue entry", () => {
  assert.equal(latestQueueStatus("queue-2", { ...waiting, status: "matched", session_id: "old-room" }), null);
  assert.equal(latestQueueStatus(null, waiting), null);
});
it("recovers a matched refresh without letting a stale waiting frame rewind it", () => {
  const matched = { ...waiting, status: "matched", session_id: "room" };
  assert.equal(latestQueueStatus("queue-1", matched, waiting), matched);
  assert.equal(latestQueueStatus("queue-1", waiting, matched), matched);
});
it("preserves server expiry against stale waiting data", () => {
  const expired = { ...waiting, status: "expired" };
  assert.equal(latestQueueStatus("queue-1", expired, waiting), expired);
});
