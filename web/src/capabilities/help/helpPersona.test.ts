import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { athenaVoiceAllowed, helpPersona } from "@/capabilities/help/helpPersona";

describe("athenaVoiceAllowed", () => {
  it("keeps the voice off Contact, Notifications, Settings and Community, in any workspace", () => {
    for (const path of [
      "/app/me/messages",
      "/app/me/notifications",
      "/app/me/inbox",
      "/app/me/settings",
      "/app/me/settings/referrals",
      "/app/acme/discussion",
    ]) {
      assert.equal(athenaVoiceAllowed(path), false, path);
    }
  });

  it("keeps it on the clinical surfaces", () => {
    for (const path of [
      "/app/me/mocks",
      "/app/me/stations/abc",
      "/app/me/summary",
      "/app/me/slides",
      "/app/me/podcast",
      "/app/me/debriefs/1",
      "/app/me/attempts/1",
      "/app/me/dashboard",
    ]) {
      assert.equal(athenaVoiceAllowed(path), true, path);
    }
  });

  it("names the dock Help where it is text only", () => {
    assert.equal(helpPersona(false).name, "Help");
    assert.equal(helpPersona(true).name, "Athena");
  });

  it("labels the jump-to row Help where it is text only", () => {
    const text = helpPersona(false);
    assert.deepEqual([text.group, text.askLabel("fees")], ["Help", "Help with \u201cfees\u201d"]);
    const voice = helpPersona(true);
    assert.deepEqual([voice.group, voice.askLabel("fees")], ["Athena", "Ask Athena about \u201cfees\u201d"]);
  });
});
