"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { useVoiceAssistant, useLocalParticipant, useConnectionState, useMaybeRoomContext } from "@livekit/components-react";
import { ConnectionState, RoomEvent, type Participant } from "livekit-client";
import {
  useScreenUiGuidance, useUiGuidance, isUiGuidanceEnabled,
  registerScreenshotRpc, registerPerformClickRpc, registerScrollRpc,
  ignoreMarkedElements,
  DATA_TYPE_NAV_MODE_CHOICE, DATA_TYPE_NAV_MODE_PROMPT, UI_GUIDANCE_SCHEMA_VERSION,
  RPC_METHOD_SCREENSHOT_CHUNKED, RPC_METHOD_PERFORM_CLICK, RPC_METHOD_SCROLL,
} from "@/foundation/livekit/guidance";

export function useHelpGuidance(voiceHelpIntent: "faq" | "guide") {
  const { state } = useVoiceAssistant();
  const pathname = usePathname();
  const { localParticipant } = useLocalParticipant();
  const connectionState = useConnectionState();
  const room = useMaybeRoomContext();
  const screenGuidanceAvailable = useScreenUiGuidance();
  const screenUiGuidanceSession =
    voiceHelpIntent === "guide" && screenGuidanceAvailable;
  const { pointerTarget, isGuidanceToolRunning, progressStep, progressLabel, cards, dismissCard } = useUiGuidance(room, {
    navigationKey: pathname,
  });
  const [navigationMode, setNavigationMode] = useState<"guide" | "automate">(
    "guide",
  );
  const navigationModeRef = useRef(navigationMode);
  useEffect(() => {
    navigationModeRef.current = navigationMode;
  }, [navigationMode]);
  const [navPromptHighlight, setNavPromptHighlight] = useState(false);

  const publishNavigationMode = useCallback(
    async (mode: "guide" | "automate") => {
      setNavigationMode(mode);
      if (!localParticipant) return;
      const payload = JSON.stringify({
        type: DATA_TYPE_NAV_MODE_CHOICE,
        schemaVersion: UI_GUIDANCE_SCHEMA_VERSION,
        mode,
      });
      await localParticipant.publishData(new TextEncoder().encode(payload), {
        reliable: true,
      });
    },
    [localParticipant],
  );

  // When LiveKit connects, the worker defaults to "guide". Re-send only if the user already
  // chose "Navigate for me" so the agent does not stay on highlights-only (avoids an extra
  // generate_reply for the default guide case). Publishing before the room is Connected is
  // silently dropped, so wait for it and send the mode at most once per payload.
  const lastNavModeSentRef = useRef<string | null>(null);
  useEffect(() => {
    if (!localParticipant || !isUiGuidanceEnabled()) return;
    if (connectionState !== ConnectionState.Connected) return;
    const mode = navigationModeRef.current;
    if (mode === "guide") return;
    const payload = JSON.stringify({
      type: DATA_TYPE_NAV_MODE_CHOICE,
      schemaVersion: UI_GUIDANCE_SCHEMA_VERSION,
      mode,
    });
    if (lastNavModeSentRef.current === payload) return;
    lastNavModeSentRef.current = payload;
    localParticipant
      .publishData(new TextEncoder().encode(payload), { reliable: true })
      .catch((err: unknown) => {
        console.error("Failed to send the navigation mode:", err);
        if (lastNavModeSentRef.current === payload) {
          lastNavModeSentRef.current = null;
        }
      });
  }, [localParticipant, connectionState]);

  useEffect(() => {
    if (!room || !isUiGuidanceEnabled()) return;
    const onData = (payload: Uint8Array, participant?: Participant) => {
      if (participant?.isLocal) return;
      try {
        const raw = JSON.parse(new TextDecoder().decode(payload)) as {
          type?: string;
        };
        if (raw?.type === DATA_TYPE_NAV_MODE_PROMPT) {
          setNavPromptHighlight(true);
          window.setTimeout(() => setNavPromptHighlight(false), 5000);
        }
      } catch {
        /* ignore */
      }
    };
    room.on(RoomEvent.DataReceived, onData);
    return () => {
      room.off(RoomEvent.DataReceived, onData);
    };
  }, [room]);

  useEffect(() => {
    if (!localParticipant || !screenUiGuidanceSession || !isUiGuidanceEnabled()) return;

    // Athena's own panel and the progress card are on screen when the capture
    // runs. Leaving them in would spend vision tokens on her own transcript and
    // let her point at her own UI.
    registerScreenshotRpc(localParticipant, {
      ignoreElements: ignoreMarkedElements,
    });
    registerPerformClickRpc(localParticipant);
    registerScrollRpc(localParticipant);

    // Without this the handlers stack up on every re-run (and twice under
    // StrictMode), which livekit-client warns about and will later throw on.
    return () => {
      localParticipant.unregisterRpcMethod(RPC_METHOD_SCREENSHOT_CHUNKED);
      localParticipant.unregisterRpcMethod(RPC_METHOD_PERFORM_CLICK);
      localParticipant.unregisterRpcMethod(RPC_METHOD_SCROLL);
    };
  }, [localParticipant, screenUiGuidanceSession]);

  const athenaDescription =
    state !== "disconnected"
      ? state === "connecting"
        ? "Connecting..."
        : screenUiGuidanceSession && isGuidanceToolRunning
          ? "Analysing your screen..."
          : !screenUiGuidanceSession && state === "thinking"
            ? "Answering..."
            : state === "speaking"
              ? "Speaking..."
              : "Listening..."
      : "Or ask Athena by voice below";

  return { state, screenUiGuidanceSession, isGuidanceToolRunning, navigationMode, navPromptHighlight,
    publishNavigationMode, pointerTarget, progressStep, progressLabel, cards, dismissCard, athenaDescription };
}
