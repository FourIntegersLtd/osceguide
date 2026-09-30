import assert from "node:assert/strict";
import { afterEach, describe, it } from "node:test";
import { browseLibrary, listStationVersions, readLibraryStation } from "@/capabilities/stations/api";

const realFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = realFetch;
});

interface Call {
  url: string;
  method: string;
}

/** Answer every request from here on with one status and body, and record them. */
function record(status: number, body: unknown): Call[] {
  const calls: Call[] = [];
  globalThis.fetch = (async (input: unknown, init?: RequestInit) => {
    calls.push({ url: String(input), method: init?.method ?? "GET" });
    return new Response(status === 204 ? null : JSON.stringify(body), {
      status,
      headers: { "content-type": "application/json" },
    });
  }) as typeof fetch;
  return calls;
}

const row = {
  id: "9f0e0f2a-2a4a-4c2b-9d37-5f1f5c0b6a11",
  title: "Chest pain, 58M",
  exam_code: "sca",
  version: 3,
  version_id: "7c1a4d3e-8b0d-4f2a-9e6c-1d2b3c4d5e6f",
  published_at: null,
};

describe("the library's own reads", () => {
  it("reads one station by id rather than walking the browse list", async () => {
    const calls = record(200, row);
    const found = await readLibraryStation(row.id);

    // One request is the whole point: the walk it replaces cost up to twenty.
    // The base is the server-side API origin, which the test does not set.
    assert.equal(calls.length, 1);
    assert.ok(calls[0]?.url.endsWith(`/api/v1/stations/${row.id}`));
    assert.equal(calls[0]?.method, "GET");
    assert.equal(found?.title, "Chest pain, 58M");
  });

  it("settles a station it may not read on null, so the screen can say so", async () => {
    record(404, { code: "station_not_found", message: "No such station" });
    assert.equal(await readLibraryStation("does-not-exist"), null);
  });

  it("keeps every other refusal a failure", async () => {
    record(403, { code: "not_entitled", message: "That exam is not yours to open" });
    await assert.rejects(() => readLibraryStation(row.id), (error: unknown) => {
      return (error as Error).message === "That exam is not yours to open";
    });
  });

  it("sends the title fragment instead of filtering the page it got", async () => {
    const calls = record(200, { items: [], next_cursor: null });
    await browseLibrary({ examCode: "sca", search: "  chest pain  ", limit: 100 });

    const url = new URL(calls[0]?.url ?? "");
    assert.equal(url.searchParams.get("search"), "chest pain");
    assert.equal(url.searchParams.get("exam_code"), "sca");
  });

  it("asks for the whole exam when the box holds nothing but spaces", async () => {
    const calls = record(200, { items: [], next_cursor: null });
    await browseLibrary({ examCode: "sca", search: "   " });

    assert.equal(new URL(calls[0]?.url ?? "").searchParams.has("search"), false);
  });

  it("reads a station's revisions newest first from its own route", async () => {
    const calls = record(200, [
      {
        id: "v2",
        station_id: row.id,
        version: 2,
        status: "published",
        content: {},
        published_at: null,
        archived_at: null,
      },
    ]);
    const versions = await listStationVersions(row.id);

    assert.ok(calls[0]?.url.endsWith(`/api/v1/stations/${row.id}/versions`));
    assert.equal(versions[0]?.version, 2);
  });
});
