"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import type { Room } from "livekit-client";
import { publishToAgent, useMicPreflight, type RoomGrant } from "@/foundation/livekit";
import { useAsync } from "@/foundation/hooks";
import { assistantSurfaceFor } from "@/capabilities/surface";
import { useSurface } from "@/capabilities/SurfaceContext";
import { assistantVoiceToken, buildClientContext, startAssistantSession } from "@/capabilities/help/api";
import { fetchOnboardingScenes, type OnboardingScene } from "@/capabilities/onboarding/api";

/** The worker's name for a scene announcement; `handlers.py` reads this exact word. */
const SCENE_CHANGE = "scene_change";

/** How long the session start waits for the microphone prompt to be answered. */
const MIC_PROMPT_WAIT_MS = 10_000;

export type OnboardingPhase = "intro" | "demo";

/**
 * One voice session for the whole walkthrough.
 *
 * Athena introduces herself, then each demo scene is *announced* to the same
 * session rather than starting a new one: the worker asks the backend to
 * re-render its instructions for the scene and the model introduces it. The
 * retiring client restarted the room per scene and cached the credentials to
 * hide the cost, which is why it also needed a fifteen-second cache and a
 * cancellation path. A session that stays up needs neither.
 */
export function useOnboardingVoice() {
  const { surface } = useSurface();
  const pathname = usePathname();
  const mic = useMicPreflight();
  const scenes = useAsync((signal) => fetchOnboardingScenes(signal), []);
  const [grant, setGrant] = useState<RoomGrant | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const roomRef = useRef<Room | null>(null);
  const announced = useRef<string | null>(null);
  const pending = useRef<Record<string, string> | null>(null);

  const start = useCallback(async () => {
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
      const session = await startAssistantSession("onboarding", context);
      setGrant(await assistantVoiceToken(session.id));
    } catch (cause) {
      setError(cause instanceof Error ? cause : new Error(String(cause)));
    } finally {
      setStarting(false);
    }
  }, [mic, pathname, surface]);

  /**
   * Tell the agent which scene is on screen.
   *
   * Held until the room is up rather than dropped: the first scene is chosen
   * while the connection is still being made, and an announcement published
   * into a room that is not connected goes nowhere — which would leave Athena
   * introducing herself over a demo the person is already reading.
   */
  const announce = useCallback((phase: OnboardingPhase, scene: OnboardingScene | null) => {
    const payload = {
      phase,
      question: scene?.question ?? "",
      patientLine: scene?.patientLine ?? "",
    };
    const key = JSON.stringify(payload);
    if (announced.current === key) return;
    announced.current = key;
    if (!roomRef.current || roomRef.current.state !== "connected") {
      pending.current = payload;
      return;
    }
    void publishToAgent(roomRef.current, SCENE_CHANGE, payload);
  }, []);

  const leave = useCallback(() => {
    void roomRef.current?.disconnect();
    roomRef.current = null;
    setGrant(null);
  }, []);

  useEffect(() => leave, [leave]);

  return {
    scenes: scenes.data?.scenes ?? [],
    assistantName: scenes.data?.persona.assistantName ?? "Athena",
    loadingScenes: scenes.loading,
    scenesError: scenes.error,
    grant,
    starting,
    error,
    mic,
    start,
    announce,
    leave,
    onConnected: (room: Room) => {
      roomRef.current = room;
      if (!pending.current) return;
      void publishToAgent(room, SCENE_CHANGE, pending.current);
      pending.current = null;
    },
  };
}
