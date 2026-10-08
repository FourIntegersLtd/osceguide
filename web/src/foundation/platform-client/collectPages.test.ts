import assert from "node:assert/strict";
import { test } from "node:test";
import { collectPages } from "@/foundation/platform-client/collectPages";

test("walks every page, however many, and passes each cursor on", async () => {
  const seen: Array<string | null> = [];
  const items = await collectPages<number>(async (cursor) => {
    seen.push(cursor);
    const page = cursor === null ? 0 : Number(cursor);
    return { items: [page], next_cursor: page < 40 ? String(page + 1) : null };
  });
  assert.equal(items.length, 41);
  assert.deepEqual(seen.slice(0, 3), [null, "1", "2"]);
});

test("throws rather than loop forever on a server that never stops returning a cursor", async () => {
  await assert.rejects(() => collectPages<number>(async () => ({ items: [1], next_cursor: "again" })), /pages/);
});
