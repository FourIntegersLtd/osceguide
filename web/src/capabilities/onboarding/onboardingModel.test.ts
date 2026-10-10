import assert from "node:assert/strict";
import { test } from "node:test";
import { meetActions, onboardingPosition, pauseToggle, sceneReply, voiceErrorCopy, voiceStatus } from "./onboardingModel";

test("a voice failure reads as whole sentences, whether or not the server's reason ends in a full stop", () => {
  assert.equal(
    voiceErrorCopy("The voice service is not available right now", "Athena"),
    "The voice service is not available right now. Athena can't speak right now. Try again, or continue without voice.",
  );
  assert.equal(
    voiceErrorCopy("We could not reach the server. Check your connection and try again.", "Athena"),
    "We could not reach the server. Check your connection and try again. Athena can't speak right now. Try again, or continue without voice.",
  );
});

test("voice is off until a grant arrives, connecting until the room is up, then on", () => {
  assert.equal(voiceStatus({ starting: false, granted: false, connected: false }), "off");
  assert.equal(voiceStatus({ starting: true, granted: false, connected: false }), "connecting");
  assert.equal(voiceStatus({ starting: false, granted: true, connected: false }), "connecting");
  assert.equal(voiceStatus({ starting: false, granted: true, connected: true }), "on");
});

test("Show me how it works waits for Athena's voice, with a way to go on without it", () => {
  assert.deepEqual(meetActions("off", "voice", "Athena"), {
    voiceButton: "Turn on Athena's voice",
    showMeEnabled: false,
    offerTextMode: true,
  });
  assert.deepEqual(meetActions("connecting", "voice", "Athena"), {
    voiceButton: "Turn on Athena's voice",
    showMeEnabled: false,
    offerTextMode: true,
  });
  assert.deepEqual(meetActions("on", "voice", "Athena"), {
    voiceButton: null,
    showMeEnabled: true,
    offerTextMode: false,
  });
  assert.deepEqual(meetActions("off", "text", "Athena"), {
    voiceButton: null,
    showMeEnabled: true,
    offerTextMode: false,
  });
});

test("the session starts where the person is: the introduction, or the scene on screen", () => {
  assert.deepEqual(onboardingPosition("meet", 2), { phase: "intro", scene: 0 });
  assert.deepEqual(onboardingPosition("demo", 1), { phase: "demo", scene: 1 });
  assert.deepEqual(onboardingPosition("invitation", 2), { phase: "intro", scene: 0 });
});

test("pausing Athena offers resuming, and the other way round", () => {
  assert.deepEqual(pauseToggle(false, "Athena"), { label: "Pause Athena", next: true });
  assert.deepEqual(pauseToggle(true, "Athena"), { label: "Resume Athena", next: false });
});

test("a typed reply is trimmed and capped, and a blank one is no reply", () => {
  assert.equal(sceneReply("   "), null);
  assert.equal(sceneReply("  What brings you in today?  "), "What brings you in today?");
  assert.equal(sceneReply("x".repeat(400))?.length, 280);
});
