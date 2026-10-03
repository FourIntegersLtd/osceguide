import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { agentStateLabel } from "@/foundation/livekit/types";

describe("agentStateLabel", () => {
  it("says the patient by default, so the consultation screen is unchanged", () => {
    assert.equal(agentStateLabel("speaking"), "The patient is speaking");
  });

  it("names Athena when she is the one on the line", () => {
    assert.equal(agentStateLabel("speaking", "Athena"), "Athena is speaking");
    assert.equal(agentStateLabel("connecting", "Athena"), "Connecting to Athena…");
    assert.equal(agentStateLabel("initializing", "Athena"), "Getting Athena ready…");
  });
});
