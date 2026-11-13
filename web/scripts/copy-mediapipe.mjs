// Copies the MediaPipe wasm runtime from node_modules into public/ so the non-verbal capture
// (capabilities/attempt-runner/nonverbal) loads it from our own origin. Runs on predev and prebuild.
import { cpSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const from = join(root, "node_modules/@mediapipe/tasks-vision/wasm");
const to = join(root, "public/mediapipe/wasm");

mkdirSync(to, { recursive: true });
cpSync(from, to, { recursive: true });
console.log("copied mediapipe wasm to public/mediapipe/wasm");
