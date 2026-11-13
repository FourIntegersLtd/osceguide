import assert from "node:assert/strict";
import { test } from "node:test";
import { frameSignal, type DetectionLike } from "./signals";

/** Column-major 4x4 matrix for a head turned `yawDeg` and tilted `pitchDeg` (rotation about Y then X). */
function matrix(yawDeg: number, pitchDeg: number): number[] {
  const y = (yawDeg * Math.PI) / 180;
  const p = (pitchDeg * Math.PI) / 180;
  const m = new Array<number>(16).fill(0);
  m[8] = Math.sin(y) * Math.cos(p);
  m[10] = Math.cos(y) * Math.cos(p);
  m[9] = -Math.sin(p);
  m[15] = 1;
  return m;
}

function result(yaw: number, pitch: number, scores: Record<string, number>): DetectionLike {
  return {
    facialTransformationMatrixes: [{ data: matrix(yaw, pitch) }],
    faceBlendshapes: [
      { categories: Object.entries(scores).map(([categoryName, score]) => ({ categoryName, score })) },
    ],
  };
}

test("a face turned 30 degrees and tilted down 10 gives those angles, smile and eyes-down means", () => {
  const signal = frameSignal(
    result(30, 10, { mouthSmileLeft: 0.4, mouthSmileRight: 0.6, eyeLookDownLeft: 0.2, eyeLookDownRight: 0.4 }),
  );
  assert.ok(signal);
  assert.equal(Math.round(signal.yaw), 30);
  assert.equal(Math.round(signal.pitch), 10);
  assert.ok(Math.abs(signal.smile - 0.5) < 1e-9);
  assert.ok(Math.abs(signal.eyesDown - 0.3) < 1e-9);
});

test("looking down is a positive pitch", () => {
  const signal = frameSignal(result(0, 20, {}));
  assert.ok(signal && signal.pitch > 19);
});

test("missing blendshapes count as zero", () => {
  const signal = frameSignal(result(0, 0, {}));
  assert.ok(signal);
  assert.equal(signal.smile, 0);
  assert.equal(signal.eyesDown, 0);
});

test("an empty result (no face) gives null", () => {
  assert.equal(frameSignal({ facialTransformationMatrixes: [], faceBlendshapes: [] }), null);
});
