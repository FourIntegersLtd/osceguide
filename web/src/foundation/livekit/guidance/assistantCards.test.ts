import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { parseKnownAssistantCard } from "@/foundation/livekit/guidance/contracts";

describe("assistant cards", () => {
  it("keeps a station suggestion the screen can draw", () => {
    const card = parseKnownAssistantCard({
      type: "assistant_card",
      card: "suggestion",
      title: "Chest pain",
      reason: "It matches what you just missed.",
      ref: { kind: "station", id: "v1", slug: null },
    });
    assert.equal(card?.card, "suggestion");
    if (card?.card === "suggestion") assert.equal(card.title, "Chest pain");
  });

  it("keeps a citation list", () => {
    const card = parseKnownAssistantCard({
      type: "assistant_card",
      card: "citations",
      citations: [{ n: 1, title: "Safety netting", section: "Chest pain", ref: { kind: "article", id: "a", slug: "safety" } }],
    });
    assert.equal(card?.card, "citations");
  });

  it("ignores a kind the screen does not know", () => {
    assert.equal(parseKnownAssistantCard({ type: "assistant_card", card: "confetti" }), null);
    assert.equal(parseKnownAssistantCard({ type: "pointer", x: 1, y: 2 }), null);
  });
});
