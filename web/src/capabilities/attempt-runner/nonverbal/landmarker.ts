// Loads the MediaPipe face landmarker once. The library is imported dynamically so it stays out
// of the main bundle; the wasm and model are served from our own origin (/mediapipe/).
import type { FaceLandmarker } from "@mediapipe/tasks-vision";

let cached: Promise<FaceLandmarker> | null = null;

/** Returns the shared landmarker, creating it on first use. A failed load is not cached. */
export function loadLandmarker(): Promise<FaceLandmarker> {
  if (!cached) {
    cached = create().catch((error: unknown) => {
      cached = null;
      throw error;
    });
  }
  return cached;
}

async function create(): Promise<FaceLandmarker> {
  const vision = await import("@mediapipe/tasks-vision");
  const fileset = await vision.FilesetResolver.forVisionTasks("/mediapipe/wasm");
  return vision.FaceLandmarker.createFromOptions(fileset, {
    baseOptions: { modelAssetPath: "/mediapipe/face_landmarker.task", delegate: "CPU" },
    runningMode: "VIDEO",
    numFaces: 1,
    outputFaceBlendshapes: true,
    outputFacialTransformationMatrixes: true,
  });
}
