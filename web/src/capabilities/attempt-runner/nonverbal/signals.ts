// Turns one MediaPipe detection result into the four numbers the sampler needs. Pure: the result
// is described structurally, so this file imports nothing from the library and runs under node:test.

/** The part of a FaceLandmarkerResult that is read (structurally compatible with the library type). */
export interface DetectionLike {
  facialTransformationMatrixes: ReadonlyArray<{ data: ArrayLike<number> }>;
  faceBlendshapes: ReadonlyArray<{ categories: ReadonlyArray<{ categoryName: string; score: number }> }>;
}

/** One frame: head angles in degrees (positive pitch = looking down), blendshape means in 0..1. */
export interface FrameSignal {
  yaw: number;
  pitch: number;
  smile: number;
  eyesDown: number;
}

const RAD_TO_DEG = 180 / Math.PI;

function mean(categories: ReadonlyArray<{ categoryName: string; score: number }>, names: [string, string]): number {
  const score = (name: string) => categories.find((c) => c.categoryName === name)?.score ?? 0;
  return (score(names[0]) + score(names[1])) / 2;
}

/** Reads head angles and smile / eyes-down means from a detection result, or null when no face was found. */
export function frameSignal(result: DetectionLike): FrameSignal | null {
  const matrix = result.facialTransformationMatrixes[0]?.data;
  if (!matrix || matrix.length < 16) return null;
  const categories = result.faceBlendshapes[0]?.categories ?? [];
  const pitchSin = Math.max(-1, Math.min(1, -(matrix[9] ?? 0)));
  return {
    yaw: Math.atan2(matrix[8] ?? 0, matrix[10] ?? 1) * RAD_TO_DEG,
    pitch: Math.asin(pitchSin) * RAD_TO_DEG,
    smile: mean(categories, ["mouthSmileLeft", "mouthSmileRight"]),
    eyesDown: mean(categories, ["eyeLookDownLeft", "eyeLookDownRight"]),
  };
}
