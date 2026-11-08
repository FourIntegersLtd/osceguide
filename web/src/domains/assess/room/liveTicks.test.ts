import assert from "node:assert/strict";
import test from "node:test";
import { createSaveQueue, saveWithRetry, type TickSave } from "@/domains/assess/room/liveTicks";

const instant = () => Promise.resolve();

test("a tick that fails twice is saved on the third try", async () => {
  let calls = 0;
  const state = await saveWithRetry(async () => { if (++calls < 3) throw new Error("x"); }, 3, instant);
  assert.deepEqual([state, calls], ["saved", 3]);
});

test("a tick that never saves ends failed, so the panel offers Retry", async () => {
  let calls = 0;
  const state = await saveWithRetry(async () => { calls++; throw new Error("x"); }, 3, instant);
  assert.deepEqual([state, calls], ["failed", 3]);
});

test("a tick made while a save is in flight is saved after it, never lost or reordered", async () => {
  const sent: number[] = [];
  const statuses: TickSave[] = [];
  let current = 1;
  let release: () => void = () => undefined;
  const queue = createSaveQueue(
    async () => {
      sent.push(current);
      if (sent.length === 1) await new Promise<void>((resolve) => { release = resolve; });
    },
    (s) => statuses.push(s),
    instant,
  );
  queue.touch();
  const first = queue.flush();
  current = 2;
  queue.touch();
  const second = queue.flush();
  release();
  await Promise.all([first, second]);
  assert.deepEqual(sent, [1, 2]);
  assert.equal(statuses.at(-1), "saved");
});

test("a failed save is retried by the next flush and still saves the latest", async () => {
  let fail = true;
  const sent: string[] = [];
  const queue = createSaveQueue(async () => { if (fail) throw new Error("x"); sent.push("ok"); }, () => undefined, instant);
  queue.touch();
  await queue.flush();
  assert.deepEqual(sent, []);
  fail = false;
  await queue.flush();
  assert.deepEqual(sent, ["ok"]);
});
