import assert from "node:assert/strict";
import { test } from "node:test";
import { acquireCamera, releaseCamera } from "./camera";

const fakeStream = () => {
  const stopped: number[] = [];
  const stream = { getTracks: () => [0, 1].map((i) => ({ stop: () => stopped.push(i) })) } as unknown as MediaStream;
  return { stream, stopped };
};

test("releaseCamera stops every track and removes the video", () => {
  const { stream, stopped } = fakeStream();
  let removed = false;
  releaseCamera(stream, { remove: () => { removed = true; } } as unknown as HTMLVideoElement);
  assert.deepEqual(stopped, [0, 1]);
  assert.equal(removed, true);
  releaseCamera(null, null);
});

test("a stream that resolves after cancellation is stopped and not returned", async () => {
  const { stream, stopped } = fakeStream();
  let cancelled = false;
  const pending = acquireCamera(async () => { cancelled = true; return stream; }, () => cancelled);
  assert.equal(await pending, null);
  assert.deepEqual(stopped, [0, 1]);
});

test("a live request returns the stream untouched", async () => {
  const { stream, stopped } = fakeStream();
  assert.equal(await acquireCamera(async () => stream, () => false), stream);
  assert.deepEqual(stopped, []);
});
