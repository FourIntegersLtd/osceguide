import assert from "node:assert/strict";
import test from "node:test";
import { browserVerdict, connectionVerdict, SLOW_MS, type BrowserEnv } from "@/domains/assess/trainee/setupChecks";

const FULL: BrowserEnv = { secureContext: true, hasMicrophoneApi: true, hasWebRtc: true, hasWebSocket: true };

test("a browser with the microphone, WebRTC and WebSocket passes", () => {
  assert.equal(browserVerdict(FULL).ok, true);
});

test("no microphone api, or an insecure page, fails with the browser advice", () => {
  for (const env of [{ ...FULL, hasMicrophoneApi: false }, { ...FULL, secureContext: false }]) {
    const verdict = browserVerdict(env);
    assert.equal(verdict.ok, false);
    assert.match(verdict.detail, /Chrome, Edge, Safari or Firefox/);
  }
});

test("missing WebRTC or WebSocket cannot join a live room", () => {
  assert.equal(browserVerdict({ ...FULL, hasWebRtc: false }).title, "This browser cannot join a live room");
  assert.equal(browserVerdict({ ...FULL, hasWebSocket: false }).ok, false);
});

test("a fast round trip is good, a slow one warns, a failed or offline one cannot reach us", () => {
  assert.equal(connectionVerdict(true, 120).ok, true);
  assert.equal(connectionVerdict(true, 120).detail, "We reached OSCE Guide in 120 ms.");
  assert.equal(connectionVerdict(true, SLOW_MS).ok, true);
  assert.equal(connectionVerdict(true, SLOW_MS + 1).title, "Your connection is slow");
  assert.equal(connectionVerdict(true, null).title, "We could not reach OSCE Guide");
  assert.equal(connectionVerdict(false, 50).ok, false);
});
