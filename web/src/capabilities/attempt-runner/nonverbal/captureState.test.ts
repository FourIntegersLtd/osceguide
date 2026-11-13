import assert from "node:assert/strict";
import { test } from "node:test";
import { loadCaptureState, saveCaptureState, seqExhausted, type KeyValueStorage } from "./captureState";

const fakeStorage = (): KeyValueStorage & { data: Map<string, string> } => {
  const data = new Map<string, string>();
  return { data, getItem: (k) => data.get(k) ?? null, setItem: (k, v) => void data.set(k, v) };
};

test("state survives a fresh in-memory cache via storage, keyed per attempt", () => {
  const storage = fakeStorage();
  saveCaptureState("A", { nextSeq: 7, startedAtMs: 100 }, storage, new Map());
  saveCaptureState("B", { nextSeq: 2, startedAtMs: 200 }, storage, new Map());
  assert.deepEqual(loadCaptureState("A", storage, new Map()), { nextSeq: 7, startedAtMs: 100 });
  assert.deepEqual(loadCaptureState("B", storage, new Map()), { nextSeq: 2, startedAtMs: 200 });
  assert.ok(storage.data.has("osce_nonverbal_seq:A"));
  assert.equal(loadCaptureState("C", storage, new Map()), null);
});

test("A to B to A keeps A's seq from the cache", () => {
  const cache = new Map();
  saveCaptureState("A", { nextSeq: 5, startedAtMs: 1 }, null, cache);
  saveCaptureState("B", { nextSeq: 1, startedAtMs: 2 }, null, cache);
  assert.equal(loadCaptureState("A", null, cache)?.nextSeq, 5);
});

test("corrupt or throwing storage yields null and does not throw", () => {
  const bad = fakeStorage();
  bad.data.set("osce_nonverbal_seq:A", "{nope");
  assert.equal(loadCaptureState("A", bad, new Map()), null);
  bad.data.set("osce_nonverbal_seq:A", JSON.stringify({ nextSeq: -1, startedAtMs: 1 }));
  assert.equal(loadCaptureState("A", bad, new Map()), null);
  const throwing: KeyValueStorage = { getItem: () => { throw new Error("x"); }, setItem: () => { throw new Error("x"); } };
  assert.equal(loadCaptureState("A", throwing, new Map()), null);
  assert.doesNotThrow(() => saveCaptureState("A", { nextSeq: 1, startedAtMs: 1 }, throwing, new Map()));
});

test("seq 400 is the last that may be posted", () => {
  assert.equal(seqExhausted(400), false);
  assert.equal(seqExhausted(401), true);
});
