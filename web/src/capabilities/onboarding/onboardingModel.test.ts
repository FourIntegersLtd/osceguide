import assert from "node:assert/strict";
import { test } from "node:test";
import {
  meetActions,
  offersSkipTour,
  onboardingPosition,
  pauseToggle,
  sceneReply,
  voiceErrorCopy,
  voiceStatus,
} from "./onboardingModel";

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

test("C-50: the choice is the step; Show me how it works only appears once voice or text is picked", () => {
  const unchosen = {
    voiceButton: "Turn on Athena's voice",
    showMe: false,
    offerTextMode: true,
    hint: "Pick voice or text first",
  };
  assert.deepEqual(meetActions("off", "voice", "Athena"), unchosen);
  assert.deepEqual(meetActions("connecting", "voice", "Athena"), { ...unchosen, hint: null });
  const chosen = { voiceButton: null, showMe: true, offerTextMode: false, hint: null };
  assert.deepEqual(meetActions("on", "voice", "Athena"), chosen);
  assert.deepEqual(meetActions("off", "text", "Athena"), chosen);
});

test("C-52: Skip tour is offered on the introduction and the demo, never on the last page", () => {
  assert.equal(offersSkipTour("meet"), true);
  assert.equal(offersSkipTour("demo"), true);
  assert.equal(offersSkipTour("invitation"), false);
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
