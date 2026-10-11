import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { askHelpRow, athenaVoiceAllowed, helpPersonaName } from "@/capabilities/help/athenaVoice";

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
    assert.equal(helpPersonaName(false), "Help");
    assert.equal(helpPersonaName(true), "Athena");
  });

  it("labels the jump-to row Help where it is text only", () => {
    assert.deepEqual(askHelpRow(false, "fees"), { group: "Help", label: "Help with \u201cfees\u201d" });
    assert.deepEqual(askHelpRow(true, "fees"), { group: "Athena", label: "Ask Athena about \u201cfees\u201d" });
  });
});
