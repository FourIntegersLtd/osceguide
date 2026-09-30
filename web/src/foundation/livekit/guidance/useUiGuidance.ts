"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Participant, Room } from "livekit-client";
import { RoomEvent } from "livekit-client";
import {
  PROGRESS_STEP_DONE,
  parseGuidanceProgressPayload,
  parseKnownAssistantCard,
  parsePointerPayload,
  TOOL_RUNNING_MESSAGE_TYPE,
  type GuidanceProgressStep,
  type KnownAssistantCard,
} from "./contracts";

export type UiGuidancePointer = {
  x: number;
  y: number;
  text?: string;
};

/** @deprecated Use `UiGuidancePointer`. */
export type PointerTarget = UiGuidancePointer;

export type UseUiGuidanceOptions = {
  navigationKey?: string | null;
};

/**
 * Everything the agent draws on the page: the pointer, and which step of a
 * guidance turn is running.
 *
 * One listener decodes every packet once. There used to be three, each with its
 * own decode and its own `isLocal` guard.
 */
export function useUiGuidance(
  room: Room | null | undefined,
  options?: UseUiGuidanceOptions,
) {
  const [pointerTarget, setPointerTarget] = useState<UiGuidancePointer | null>(null);
  const [progressStep, setProgressStep] = useState<GuidanceProgressStep | null>(null);
  const [progressLabel, setProgressLabel] = useState<string | null>(null);
  const [legacyToolRunning, setLegacyToolRunning] = useState(false);
  const [cards, setCards] = useState<KnownAssistantCard[]>([]);
  const prevNavigationKeyRef = useRef<string | null | undefined>(undefined);

  // A worker from before the progress panel only sends `tool_running`.
  const isGuidanceToolRunning = progressStep !== null || legacyToolRunning;

  useEffect(() => {
    const key = options?.navigationKey;
    if (key === undefined) return;
    if (prevNavigationKeyRef.current !== undefined && prevNavigationKeyRef.current !== key) {
      setPointerTarget(null);
    }
    prevNavigationKeyRef.current = key;
  }, [options?.navigationKey]);

  // A highlight from the previous step would point at a page that has moved on.
  const [prevGuidanceToolRunning, setPrevGuidanceToolRunning] = useState(isGuidanceToolRunning);
  if (isGuidanceToolRunning !== prevGuidanceToolRunning) {
    setPrevGuidanceToolRunning(isGuidanceToolRunning);
    if (isGuidanceToolRunning) setPointerTarget(null);
  }

  useEffect(() => {
    if (!room) return;

    const onData = (payloadBytes: Uint8Array, sender?: Participant) => {
      if (sender?.isLocal) return;

      let message: Record<string, unknown>;
      try {
        message = JSON.parse(new TextDecoder().decode(payloadBytes)) as Record<string, unknown>;
      } catch {
        return; // not ours
      }

      const card = parseKnownAssistantCard(message);
      if (card) {
        setCards((current) => [...current.filter((existing) => existing.card !== card.card), card]);
        return;
      }

      const progress = parseGuidanceProgressPayload(message);
      if (progress) {
        const finished = progress.step === PROGRESS_STEP_DONE;
        setProgressStep(finished ? null : progress.step);
        setProgressLabel(finished ? null : (progress.label ?? null));
        return;
      }

      if (message?.type === TOOL_RUNNING_MESSAGE_TYPE) {
        setLegacyToolRunning(message.active === true);
        return;
      }

      const pointer = parsePointerPayload(message);
      if (!pointer) return;
      setPointerTarget(pointer.clear ? null : { x: pointer.x, y: pointer.y, text: pointer.text });
    };

    room.on(RoomEvent.DataReceived, onData);

    return () => {
      room.off(RoomEvent.DataReceived, onData);
      // A disconnect mid-guidance used to leave the cursor stranded on screen.
      setPointerTarget(null);
      setProgressStep(null);
      setProgressLabel(null);
      setLegacyToolRunning(false);
      setCards([]);
    };
  }, [room]);

  const clearPointerTarget = useCallback(() => setPointerTarget(null), []);
  const dismissCard = useCallback((kind: KnownAssistantCard["card"]) => {
    setCards((current) => current.filter((card) => card.card !== kind));
  }, []);

  return {
    pointerTarget,
    setPointerTarget,
    clearPointerTarget,
    isGuidanceToolRunning,
    progressStep,
    progressLabel,
    cards,
    dismissCard,
  };
}
