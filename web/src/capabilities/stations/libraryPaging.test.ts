import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { PlatformError } from "@/foundation/platform-client";
import { pageAcrossLegs, uniqueById, type LibraryLegs } from "@/capabilities/stations/libraryPaging";
import type { LibraryPage, LibraryStation } from "@/capabilities/stations/api";

const station = (id: string): LibraryStation => ({ id }) as LibraryStation;
const page = (ids: string[], next: string | null = null): LibraryPage => ({
  items: ids.map(station),
  next_cursor: next,
});
const ids = (p: LibraryPage) => p.items.map((s) => s.id);
const refused = (status: number) =>
  new PlatformError(status, { code: "not_entitled", message: "no" } as ConstructorParameters<typeof PlatformError>[1]);

describe("pageAcrossLegs", () => {
  it("rolls from an exhausted org leg into the platform leg", async () => {
    const legs: LibraryLegs = {
      org: async () => page(["a"]),
      platform: async () => page(["b"], "p2"),
    };
    const result = await pageAcrossLegs(legs, true, null);
    assert.deepEqual(ids(result), ["a", "b"]);
    assert.equal(result.next_cursor, "platform:p2");
  });

  it("an unentitled platform leg is a failure to show, never an empty list", async () => {
    const legs: LibraryLegs = {
      org: async () => page(["a"]),
      platform: async () => {
        throw refused(403);
      },
    };
    await assert.rejects(pageAcrossLegs(legs, true, null), { status: 403, code: "not_entitled" });
    await assert.rejects(pageAcrossLegs(legs, true, "platform:x"), { status: 403 });
  });

  it("keeps the org cursor while the org leg has more, and skips the platform when told to", async () => {
    const legs: LibraryLegs = {
      org: async () => page(["a"], "o2"),
      platform: async () => {
        throw new Error("not reached");
      },
    };
    assert.equal((await pageAcrossLegs(legs, true, null)).next_cursor, "o2");
    assert.equal((await pageAcrossLegs({ ...legs, org: async () => page(["a"]) }, false, null)).next_cursor, null);
  });

  it("a 4xx other than not_entitled still raises", async () => {
    const legs: LibraryLegs = {
      org: async () => page([]),
      platform: async () => {
        throw refused(404);
      },
    };
    await assert.rejects(pageAcrossLegs(legs, true, null));
  });

  it("a server error on the platform leg still raises", async () => {
    const legs: LibraryLegs = {
      org: async () => page([]),
      platform: async () => {
        throw refused(500);
      },
    };
    await assert.rejects(pageAcrossLegs(legs, true, null));
  });
});

describe("uniqueById", () => {
  it("shows a repeated station once, first seen first", () => {
    assert.deepEqual(uniqueById(["a", "b", "a", "c", "b"].map(station)).map((s) => s.id), ["a", "b", "c"]);
  });
});
