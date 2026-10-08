import assert from "node:assert/strict";
import { afterEach, describe, it } from "node:test";
import { listStationTemplates } from "@/capabilities/authoring/api/templates";

const realFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = realFetch;
});

describe("listStationTemplates", () => {
  it("walks every page, however many there are", async () => {
    let calls = 0;
    globalThis.fetch = (async () => {
      calls += 1;
      const last = calls === 25;
      return new Response(
        JSON.stringify({
          items: [{ id: `t${calls}`, title: `T${calls}`, versions: [] }],
          next_cursor: last ? null : `c${calls}`,
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    }) as typeof fetch;
    const result = await listStationTemplates({ base: "/api/v1/orgs/kings", kind: "org" });
    assert.equal(result.items.length, 25);
    assert.equal(result.items[24]?.id, "t25");
  });
});
