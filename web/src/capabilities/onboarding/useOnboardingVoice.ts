"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import type { Room } from "livekit-client";
import { publishToAgent, useMicPreflight, type RoomGrant } from "@/foundation/livekit";
import { useAsync } from "@/foundation/hooks";
import { assistantSurfaceFor } from "@/capabilities/surface";
import { useSurface } from "@/capabilities/SurfaceContext";
import { assistantVoiceToken, buildClientContext, startAssistantSession, type OnboardingStart } from "@/capabilities/help/api";
import { fetchOnboardingScenes, type OnboardingScene } from "@/capabilities/onboarding/api";
import { voiceStatus } from "@/capabilities/onboarding/onboardingModel";

/** The worker's name for a scene announcement; `handlers.py` reads this exact word. */
const SCENE_CHANGE = "scene_change";

/** How long the session start waits for the microphone prompt to be answered. */
const MIC_PROMPT_WAIT_MS = 10_000;

/** One empty list, so `announce` keeps its identity while the scenes load. */
const NO_SCENES: OnboardingScene[] = [];

/**
 * One voice session for the whole walkthrough.
 *
 * The session starts on the step the person is on (`start(position)`), so
 * turning voice on mid-demo narrates that scene, not the introduction. Each
 * later scene is *announced* to the same session rather than starting a new
 * one: the worker asks the backend to re-render its instructions for the
 * scene and the model introduces it.
 */
export function useOnboardingVoice() {
  const { surface } = useSurface();
  const pathname = usePathname();
  const mic = useMicPreflight();
  const scenes = useAsync((signal) => fetchOnboardingScenes(signal), []);
  const [grant, setGrant] = useState<RoomGrant | null>(null);
  const [starting, setStarting] = useState(false);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const roomRef = useRef<Room | null>(null);
  const announced = useRef<string | null>(null);
  const sceneList = scenes.data?.scenes ?? NO_SCENES;

  const start = useCallback(
    async (position: OnboardingStart) => {
      setStarting(true);
      setError(null);
      try {
        // Bounded: an installed iOS app can leave the permission request
        // unanswered for good, and waiting on it kept the walkthrough loading
        // for ever. Athena can still speak without the microphone.
        if (mic.status !== "ready") {
          await Promise.race([
            mic.request(),
            new Promise((resolve) => setTimeout(resolve, MIC_PROMPT_WAIT_MS)),
          ]);
        }
        const context = buildClientContext({ surface: assistantSurfaceFor(surface), pathname });
        const session = await startAssistantSession("onboarding", context, { onboarding: position });
        // The session opens on this position, so announcing it again would
        // only cut off Athena's opening line to say the same thing.
        announced.current = JSON.stringify(position);
        setGrant(await assistantVoiceToken(session.id));
      } catch (cause) {
        setError(cause instanceof Error ? cause : new Error(String(cause)));
      } finally {
        setStarting(false);
      }
    },
    [mic, pathname, surface],
  );

  /**
   * Tell the agent which step is on screen, once the room is up.
   *
   * The caller re-announces when `connected` turns true, so a step changed
   * while the room was still connecting is announced then rather than lost.
   */
  const announce = useCallback(
    (position: OnboardingStart) => {
      const room = roomRef.current;
      if (!room || room.state !== "connected") return;
      const key = JSON.stringify(position);
      if (announced.current === key) return;
      announced.current = key;
      const scene = position.phase === "demo" ? sceneList[position.scene] : undefined;
      void publishToAgent(room, SCENE_CHANGE, {
        phase: position.phase,
        question: scene?.question ?? "",
        patientLine: scene?.patientLine ?? "",
      });
    },
    [sceneList],
  );

  const leave = useCallback(() => {
    void roomRef.current?.disconnect();
    roomRef.current = null;
    setConnected(false);
    setGrant(null);
  }, []);

  useEffect(() => leave, [leave]);

  return {
    scenes: sceneList,
    assistantName: scenes.data?.persona.assistantName ?? "Athena",
    loadingScenes: scenes.loading,
    scenesError: scenes.error,
    grant,
    starting,
    status: voiceStatus({ starting, granted: Boolean(grant), connected }),
    error,
    mic,
    start,
    announce,
    leave,
    onConnected: (room: Room) => {
      roomRef.current = room;
      setConnected(true);
    },
    onDisconnected: () => setConnected(false),
  };
}
