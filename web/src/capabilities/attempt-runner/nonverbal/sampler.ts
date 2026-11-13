// Folds per-frame signals into one sample per second. Pure: the caller passes the clock in.
import type { FrameSignal } from "./signals";

/** One second of capture (the shared vocabulary: field names match the api batch body). */
export interface Sample {
  at_ms: number;
  face: boolean;
  away: boolean;
  yaw: number;
  pitch: number;
  smile: number;
  nod: boolean;
}

const BASELINE_FRAMES = 12;
const AWAY_YAW = 25;
const AWAY_PITCH = 18;
const AWAY_EYES_DOWN = 0.6;
const NOD_WINDOW_MS = 1500;
const NOD_RISE = 6;
const NOD_RETURN = 3;
const BUCKET_MS = 1000;

interface Seen {
  yaw: number;
  pitch: number;
  smile: number;
  away: boolean;
}

interface NodWindow {
  startMs: number;
  startPitch: number;
  peaked: boolean;
}

function median(values: number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? (sorted[mid] ?? 0) : ((sorted[mid - 1] ?? 0) + (sorted[mid] ?? 0)) / 2;
}

const mean = (values: number[]): number => values.reduce((a, b) => a + b, 0) / values.length;

/** Collects frames and emits one Sample each time a second has passed. */
export class Sampler {
  private baselineYaw: number[] = [];
  private baselinePitch: number[] = [];
  private bucketStart: number | null = null;
  private total = 0;
  private faces: Seen[] = [];
  private nodded = false;
  private nodWindow: NodWindow | null = null;

  /** Adds a frame (null when no face); returns the finished sample when a second has passed. */
  push(frame: FrameSignal | null, nowMs: number): Sample | null {
    let emitted: Sample | null = null;
    if (this.bucketStart === null) {
      this.bucketStart = nowMs;
    } else if (nowMs - this.bucketStart >= BUCKET_MS) {
      emitted = this.finish(this.bucketStart + BUCKET_MS);
      this.bucketStart = nowMs;
    }
    this.total += 1;
    if (frame) this.addFace(frame, nowMs);
    return emitted;
  }

  private addFace(frame: FrameSignal, nowMs: number): void {
    if (this.baselineYaw.length < BASELINE_FRAMES) {
      this.baselineYaw.push(frame.yaw);
      this.baselinePitch.push(frame.pitch);
    }
    const yaw = frame.yaw - median(this.baselineYaw);
    const pitch = frame.pitch - median(this.baselinePitch);
    const away = Math.abs(yaw) > AWAY_YAW || pitch > AWAY_PITCH || frame.eyesDown > AWAY_EYES_DOWN;
    this.faces.push({ yaw, pitch, smile: frame.smile, away });
    if (this.trackNod(pitch, nowMs)) this.nodded = true;
  }

  /** True when this frame completes a nod: up at least 6 degrees inside 1.5 s, then back within 3. */
  private trackNod(pitch: number, nowMs: number): boolean {
    const w = this.nodWindow;
    if (!w || nowMs - w.startMs > NOD_WINDOW_MS) {
      this.nodWindow = { startMs: nowMs, startPitch: pitch, peaked: false };
      return false;
    }
    if (pitch - w.startPitch >= NOD_RISE) {
      w.peaked = true;
    } else if (w.peaked && Math.abs(pitch - w.startPitch) <= NOD_RETURN) {
      this.nodWindow = { startMs: nowMs, startPitch: pitch, peaked: false };
      return true;
    } else if (!w.peaked && pitch < w.startPitch) {
      w.startPitch = pitch;
    }
    return false;
  }

  private finish(atMs: number): Sample {
    const face = this.faces.length * 2 >= this.total && this.faces.length > 0;
    const away = face && this.faces.filter((f) => f.away).length * 2 >= this.faces.length;
    const sample: Sample = {
      at_ms: atMs,
      face,
      away,
      yaw: face ? Math.round(mean(this.faces.map((f) => f.yaw))) : 0,
      pitch: face ? Math.round(mean(this.faces.map((f) => f.pitch))) : 0,
      smile: face ? Math.round(mean(this.faces.map((f) => f.smile)) * 100) : 0,
      nod: this.nodded,
    };
    this.total = 0;
    this.faces = [];
    this.nodded = false;
    return sample;
  }
}
