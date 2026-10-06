import assert from "node:assert/strict";
import { it } from "node:test";
import { listenForSnapshots, shouldRetry, streamUrl } from "./eventStreamProtocol";

it("connects through a same-origin proxy with an encoded stream ticket", () => {
  const url = new URL(streamUrl("", "/api/v1/me/practice-sessions/one/stream", "http://localhost:3100", "ticket+one"));
  assert.equal(url.origin, "http://localhost:3100");
  assert.equal(url.pathname, "/api/v1/me/practice-sessions/one/stream");
  assert.equal(url.searchParams.get("ticket"), "ticket+one");
  assert.equal(new URL(streamUrl("https://api.example.com", "/stream", "https://app.example.com", "t")).origin, "https://api.example.com");
});
it("delivers backend snapshot phases, ignores heartbeats, and cleans up", () => {
  const source = new EventTarget();
  const phases: string[] = [];
  const stop = listenForSnapshots<{ current_phase: string }>(source, (snapshot) => phases.push(snapshot.current_phase));
  source.dispatchEvent(new MessageEvent("connected", { data: "{}" }));
  source.dispatchEvent(new MessageEvent("snapshot", { data: '{"current_phase":"preparation"}' }));
  source.dispatchEvent(new MessageEvent("ping", { data: "{}" }));
  source.dispatchEvent(new MessageEvent("snapshot", { data: '{"current_phase":"consultation"}' }));
  source.dispatchEvent(new MessageEvent("snapshot", { data: "invalid" }));
  stop();
  source.dispatchEvent(new MessageEvent("snapshot", { data: '{"current_phase":"debrief"}' }));
  assert.deepEqual(phases, ["preparation", "consultation"]);
});
it("does not retry a refused ticket but retries other failures", () => {
  assert.equal(shouldRetry(401), false);
  assert.equal(shouldRetry(403), false);
  assert.equal(shouldRetry(500), true);
  assert.equal(shouldRetry(undefined), true);
});
