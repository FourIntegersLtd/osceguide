import assert from "node:assert/strict";
import { afterEach, describe, it } from "node:test";
import { readAthenaLaunch, startAssistantSession, type AssistantClientContext } from "@/capabilities/help/api";

const realFetch = globalThis.fetch;
const context: AssistantClientContext = { surface: "exam", route: "/app/me/library/asthma", navigation: [] };

afterEach(() => {
  globalThis.fetch = realFetch;
});

/** Answers every request with a session and keeps the bodies that were sent. */
function captureBodies(): unknown[] {
  const bodies: unknown[] = [];
  globalThis.fetch = (async (_input: unknown, init?: RequestInit) => {
    bodies.push(JSON.parse(String(init?.body)));
    return new Response(JSON.stringify({ id: "session-1" }), {
      status: 201,
      headers: { "content-type": "application/json" },
    });
  }) as typeof fetch;
  return bodies;
}

describe("opening Athena on a topic", () => {
  it("sends the topic or the onboarding step with the session, and nothing when there is none", async () => {
    const bodies = captureBodies();
    await startAssistantSession("dashboard", context, {
      topic: { title: "Asthma", kind: "summary", slug: "asthma" },
    });
    await startAssistantSession("dashboard", context);
    await startAssistantSession("onboarding", context, { onboarding: { phase: "demo", scene: 1 } });

    assert.deepEqual(bodies, [
      {
        session_type: "dashboard",
        extras: { client: context, topic: { title: "Asthma", kind: "summary", slug: "asthma" } },
      },
      { session_type: "dashboard", extras: { client: context } },
      { session_type: "onboarding", extras: { client: context, onboarding: { phase: "demo", scene: 1 } } },
    ]);
  });

  it("reads the launch event, ignoring a topic with no title", () => {
    assert.deepEqual(readAthenaLaunch({ kind: "athena", topic: { title: " Chest pain ", kind: "summary" } }), {
      kind: "athena",
      topic: { title: "Chest pain", kind: "summary" },
    });
    assert.deepEqual(readAthenaLaunch({ kind: "onboarding" }), { kind: "onboarding", topic: null });
    assert.deepEqual(readAthenaLaunch({ kind: "athena", topic: { title: "  " } }), { kind: "athena", topic: null });
    assert.deepEqual(readAthenaLaunch(undefined), { kind: "athena", topic: null });
  });
});
