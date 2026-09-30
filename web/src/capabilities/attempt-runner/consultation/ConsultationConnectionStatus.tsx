"use client";

import { ConnectionQualityIndicator, useConnectionState, useLocalParticipant } from "@livekit/components-react";
import { ConnectionState } from "livekit-client";
import { HiOutlineMicrophone } from "react-icons/hi2";

export function ConsultationConnectionStatus() {
  const state = useConnectionState();
  const { localParticipant, isMicrophoneEnabled, lastMicrophoneError } = useLocalParticipant();
  const connected = state === ConnectionState.Connected;
  const level = localParticipant.audioLevel;
  const mic = lastMicrophoneError ? "Mic blocked" : !connected ? "Preparing mic…"
    : !isMicrophoneEnabled ? "Mic off" : !localParticipant.isSpeaking ? "Mic ready"
      : level < 0.05 ? "Speak up a little" : level < 0.9 ? "Mic hears you" : "Very loud";
  return (
    <div className="mb-4 flex justify-center" role="status" aria-live="polite">
      <div className="flex max-w-full items-center gap-1.5 rounded-full bg-b2c-secondary p-1.5 sm:gap-2 sm:p-2">
        <ConnectionQualityIndicator participant={localParticipant} className="h-3.5 w-3.5 text-osce-success-text sm:h-5 sm:w-5" />
        <span className="whitespace-nowrap text-osce-caption text-osce-success-text sm:text-osce-body">{connected ? "Connected" : "Reconnecting…"}</span>
        <div className="mx-1 hidden h-4 border-l border-b2c-border sm:mx-2 sm:block sm:h-5" />
        <HiOutlineMicrophone className="h-3.5 w-3.5 text-b2c-text-secondary sm:h-4 sm:w-4" aria-hidden />
        <span className="whitespace-nowrap text-osce-caption text-b2c-text-muted sm:text-osce-body">{mic}</span>
      </div>
    </div>
  );
}
