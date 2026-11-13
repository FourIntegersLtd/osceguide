import assert from "node:assert/strict";
import { test } from "node:test";
import { Sampler, type Sample } from "./sampler";
import type { FrameSignal } from "./signals";

const frame = (over: Partial<FrameSignal> = {}): FrameSignal => ({
  yaw: 0,
  pitch: 0,
  smile: 0,
  eyesDown: 0,
  ...over,
});

/** Push frames every `stepMs` from `fromMs` (inclusive) up to `toMs` (exclusive); return emitted samples. */
function run(
  sampler: Sampler,
  fromMs: number,
  toMs: number,
  stepMs: number,
  make: (t: number) => FrameSignal | null,
): Sample[] {
  const out: Sample[] = [];
  for (let t = fromMs; t < toMs; t += stepMs) {
    const sample = sampler.push(make(t), t);
    if (sample) out.push(sample);
  }
  return out;
}

test("a steady face gives away false and no nod", () => {
  const samples = run(new Sampler(), 0, 4000, 100, () => frame({ smile: 0.3 }));
  assert.equal(samples.length, 3);
  for (const s of samples) {
    assert.equal(s.face, true);
    assert.equal(s.away, false);
    assert.equal(s.nod, false);
    assert.equal(s.smile, 30);
  }
});

test("head turned 40 degrees for 3 seconds gives three away samples", () => {
  const sampler = new Sampler();
  const out = run(sampler, 0, 600, 50, () => frame()); // 12 baseline frames
  out.push(...run(sampler, 1000, 4100, 100, () => frame({ yaw: 40 })));
  assert.deepEqual(
    out.map((s) => s.away),
    [false, true, true, true],
  );
  assert.equal(out[1]?.yaw, 40);
});

test("looking down by eyes alone is away", () => {
  const sampler = new Sampler();
  const out = run(sampler, 0, 3100, 100, () => frame({ eyesDown: 0.8 }));
  assert.ok(out.length > 0 && out.every((s) => s.away));
});

test("a down-and-up pitch curve gives exactly one nod", () => {
  const pitchAt = (t: number) => (t >= 1000 && t < 1300 ? 10 : 0);
  const out = run(new Sampler(), 0, 3100, 100, (t) => frame({ pitch: pitchAt(t) }));
  assert.equal(out.filter((s) => s.nod).length, 1);
  assert.equal(out.length, 3);
});

test("no faces gives face false and away false", () => {
  const out = run(new Sampler(), 0, 2100, 100, () => null);
  assert.equal(out.length, 2);
  for (const s of out) {
    assert.equal(s.face, false);
    assert.equal(s.away, false);
  }
});

test("a baseline pitch of 15 degrees is subtracted", () => {
  const out = run(new Sampler(), 0, 3100, 100, () => frame({ pitch: 15 }));
  assert.ok(out.length > 0);
  for (const s of out) {
    assert.equal(s.pitch, 0);
    assert.equal(s.away, false);
  }
});

test("a sample is stamped with the end of its second", () => {
  const out = run(new Sampler(), 5000, 6200, 100, () => frame());
  assert.equal(out[0]?.at_ms, 6000);
});
