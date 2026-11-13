import assert from "node:assert/strict";
import { test } from "node:test";
import { Batcher } from "./batcher";
import type { Sample } from "./sampler";

const sample = (n: number): Sample => ({ at_ms: n * 1000, face: true, away: false, yaw: 0, pitch: 0, smile: 0, nod: false });

test("a batch is released every tenth sample, numbered from zero", () => {
  const b = new Batcher(10);
  for (let i = 0; i < 9; i++) assert.equal(b.add(sample(i), 5), null);
  const first = b.add(sample(9), 5);
  assert.equal(first?.seq, 0);
  assert.equal(first?.samples.length, 10);
  assert.equal(first?.client_sent_at_ms, 5);
  for (let i = 10; i < 19; i++) b.add(sample(i), 5);
  assert.equal(b.add(sample(19), 6)?.seq, 1);
});

test("flush releases what is left once, and nothing when empty", () => {
  const b = new Batcher(10);
  b.add(sample(0), 1);
  b.add(sample(1), 1);
  assert.equal(b.flush(2)?.samples.length, 2);
  assert.equal(b.flush(3), null);
});

test("a resumed batcher continues the seq of the one before it", () => {
  const first = new Batcher(2);
  first.add(sample(0), 1);
  assert.equal(first.add(sample(1), 1)?.seq, 0);
  first.add(sample(2), 2);
  assert.equal(first.flush(2)?.seq, 1);
  const resumed = new Batcher(2, first.nextSeq);
  resumed.add(sample(3), 3);
  assert.equal(resumed.add(sample(4), 3)?.seq, 2);
});
