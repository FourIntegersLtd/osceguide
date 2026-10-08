import assert from "node:assert/strict";
import { afterEach, describe, it } from "node:test";
import { listProgrammes } from "@/domains/assess/api";

const realFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = realFetch;
});

describe("an organisation's programmes", () => {
  it("are read past the first page", async () => {
    const pages: Record<string, unknown> = {
      first: { items: [{ id: "p1" }, { id: "p2" }], next_cursor: "second" },
      second: { items: [{ id: "p3" }], next_cursor: null },
    };
    globalThis.fetch = (async (input: RequestInfo | URL) => {
      const cursor = new URL(String(input), "http://x").searchParams.get("cursor");
      return new Response(JSON.stringify(pages[cursor ?? "first"]), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }) as typeof fetch;
    const page = await listProgrammes("kings");
    assert.deepEqual(page.items.map((item) => item.id), ["p1", "p2", "p3"]);
  });
});
