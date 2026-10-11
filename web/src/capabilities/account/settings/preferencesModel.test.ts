import assert from "node:assert/strict";
import { test } from "node:test";
import { preferencePatch } from "@/capabilities/account/settings/preferencesModel";

const timers = { readingSeconds: 240, simulationSeconds: 840 };

test("each switch sends only its own field, so PATCH /me leaves the rest alone", () => {
  assert.deepEqual(preferencePatch("ai_training_consent", true), { ai_training_consent: true });
  assert.deepEqual(preferencePatch("ai_training_consent", false), { ai_training_consent: false });
  assert.deepEqual(preferencePatch("colleague_waiting_email", true), { colleague_waiting_email: true });
});

test("turning extra reading time on sends the confirmed timers with it", () => {
  assert.deepEqual(preferencePatch("needs_extra_time", true, timers), {
    needs_extra_time: true,
    custom_reading_seconds: 240,
    custom_simulation_seconds: 840,
  });
});

test("turning extra reading time off keeps the saved timers for next time", () => {
  assert.deepEqual(preferencePatch("needs_extra_time", false, timers), { needs_extra_time: false });
});
