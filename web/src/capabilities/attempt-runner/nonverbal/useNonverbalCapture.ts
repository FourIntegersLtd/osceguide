"use client";

import { useEffect, useState } from "react";
import { PlatformError } from "@/foundation/platform-client";
import { postNonverbalBatch, type NonverbalBatch } from "./api";
import { Batcher } from "./batcher";
import { acquireCamera, releaseCamera } from "./camera";
import { loadLandmarker } from "./landmarker";
import { loadCaptureState, saveCaptureState, seqExhausted } from "./captureState";
import { Sampler, type Sample } from "./sampler";
import { frameSignal } from "./signals";
import { FrameThrottle } from "./throttle";

export type CaptureStatus = "idle" | "starting" | "running" | "denied" | "unavailable";

const BATCH_SIZE = 10;
const KEEP_SAMPLES = 900;

/** A one-pixel, invisible video the analysis reads from. It stays in the page whichever tab or column is showing. */
function analysisVideo(stream: MediaStream): HTMLVideoElement {
  const video = document.createElement("video");
  video.muted = true;
  video.playsInline = true;
  video.setAttribute("aria-hidden", "true");
  video.style.cssText = "position:fixed;bottom:0;left:0;width:1px;height:1px;opacity:0;pointer-events:none";
  video.srcObject = stream;
  document.body.appendChild(video);
  return video;
}

/** A refusal (every `nonverbal_` code) means consent is gone, stale, or the attempt cannot take cues. */
function isRefusal(error: unknown): boolean {
  if (!(error instanceof PlatformError)) return false;
  switch (error.code) {
    case "nonverbal_consent_required":
    case "nonverbal_consent_version_stale":
    case "nonverbal_not_available":
      return true;
    default:
      return false;
  }
}

/**
 * Runs the camera, the face landmarker and the sampler while `active`, entirely on this device.
 * The stream is never published to the room. Every tenth sample is posted as a batch; a failed
 * post is dropped so the consultation is never interrupted, and a refusal (any `nonverbal_` code)
 * releases the camera, stops posting and calls `onRefused` so the consent is re-read.
 * Frames come from requestVideoFrameCallback (requestAnimationFrame as a fallback), not a timer.
 */
export function useNonverbalCapture({ attemptId, active, onRefused }: { attemptId: string | null; active: boolean; onRefused?: () => void }) {
  const [status, setStatus] = useState<CaptureStatus>("idle");
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [startedAtMs, setStartedAtMs] = useState<number | null>(null);

  // Samples belong to one attempt: drop them when it changes.
  useEffect(() => {
    setSamples([]);
    setStartedAtMs(null);
  }, [attemptId]);

  useEffect(() => {
    if (!active || !attemptId) return;
    let cancelled = false;
    let posting = true;
    let media: MediaStream | null = null;
    let video: HTMLVideoElement | null = null;
    let cancelFrame: () => void = () => {};
    // Per-attempt state outlives this effect: the server drops a repeated (attempt, seq), and offsets must not go negative.
    const prior = loadCaptureState(attemptId);
    const attemptStartedAt = prior?.startedAtMs ?? Date.now();
    const batcher = new Batcher(BATCH_SIZE, prior?.nextSeq ?? 0);
    const persist = () => saveCaptureState(attemptId, { nextSeq: batcher.nextSeq, startedAtMs: attemptStartedAt });
    persist();

    /** Stop the loop and give the camera back; safe to call twice. */
    const release = () => {
      cancelFrame();
      releaseCamera(media, video);
      media = null;
      video = null;
      setStream(null);
    };
    const fail = (next: CaptureStatus) => {
      cancelled = true;
      release();
      setStatus(next);
    };

    const send = (batch: NonverbalBatch | null) => {
      if (!batch || !posting) return;
      persist();
      if (seqExhausted(batch.seq)) return;
      postNonverbalBatch(attemptId, batch).catch((error: unknown) => {
        if (!isRefusal(error)) return;
        posting = false;
        cancelled = true;
        release();
        setStatus("idle");
        onRefused?.();
      });
    };

    const start = async () => {
      setStatus("starting");
      try {
        media = await acquireCamera(
          () => navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480, facingMode: "user" } }),
          () => cancelled,
        );
      } catch {
        if (!cancelled) setStatus("denied");
        return;
      }
      if (!media) return;
      try {
        const landmarker = await loadLandmarker();
        if (cancelled) return;
        const el = analysisVideo(media);
        video = el;
        await el.play();
        if (cancelled) return;
        const sampler = new Sampler();
        const throttle = new FrameThrottle();
        const onFrame = () => {
          if (cancelled) return;
          const now = performance.now();
          if (throttle.shouldProcess(now)) {
            let result;
            try {
              result = landmarker.detectForVideo(el, now);
            } catch {
              fail("unavailable");
              return;
            }
            throttle.record(performance.now() - now);
            const sample = sampler.push(frameSignal(result), Date.now());
            if (sample) {
              setSamples((prev) => [...prev, sample].slice(-KEEP_SAMPLES));
              send(batcher.add(sample, Date.now()));
            }
          }
          if (!cancelled) schedule();
        };
        const schedule = () => {
          if (typeof el.requestVideoFrameCallback === "function") {
            const id = el.requestVideoFrameCallback(onFrame);
            cancelFrame = () => el.cancelVideoFrameCallback(id);
          } else {
            const id = requestAnimationFrame(onFrame);
            cancelFrame = () => cancelAnimationFrame(id);
          }
        };
        setStream(media);
        setStartedAtMs(attemptStartedAt);
        setStatus("running");
        schedule();
      } catch {
        // The landmarker failed to load or play() threw: give the camera back, not just on cleanup.
        if (!cancelled) fail("unavailable");
        else release();
      }
    };
    void start();

    return () => {
      cancelled = true;
      send(batcher.flush(Date.now()));
      persist();
      release();
      setStatus("idle");
    };
  }, [attemptId, active, onRefused]);

  return { status, stream, samples, startedAtMs };
}

export type NonverbalCapture = ReturnType<typeof useNonverbalCapture>;
