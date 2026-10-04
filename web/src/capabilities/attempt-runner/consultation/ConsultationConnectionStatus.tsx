"use client";

import { ConnectionQualityIndicator, useConnectionState, useLocalParticipant } from "@livekit/components-react";
import { ConnectionState } from "livekit-client";
import { HiOutlineMicrophone } from "react-icons/hi2";
import { Button, cn } from "@/foundation/ui";
import { micStatus } from "./micStatus";

export function ConsultationConnectionStatus() {
  const state = useConnectionState();
  const { localParticipant, isMicrophoneEnabled, lastMicrophoneError } = useLocalParticipant();
  const connected = state === ConnectionState.Connected;
  const mic = micStatus({
    blocked: Boolean(lastMicrophoneError),
    connected,
    enabled: isMicrophoneEnabled,
    speaking: localParticipant.isSpeaking,
    level: localParticipant.audioLevel,
  });
  return (
    <div className="mb-4 space-y-3" role="status" aria-live="polite">
      <div className="flex justify-center">
        <div className="flex max-w-full items-center gap-2 rounded-full border border-osce-border bg-b2c-surface-muted px-3 py-1.5">
          <ConnectionQualityIndicator participant={localParticipant} className="h-3.5 w-3.5 text-osce-ink-900" />
          <span className="whitespace-nowrap text-osce-meta text-osce-ink-900">{connected ? "Connected" : "Reconnecting…"}</span>
          <span className="h-4 border-l border-osce-border" aria-hidden />
          <HiOutlineMicrophone className="h-3.5 w-3.5 text-b2c-text-muted" aria-hidden />
          <span className={cn("whitespace-nowrap text-osce-meta", lastMicrophoneError ? "text-osce-danger-text" : "text-b2c-text-muted")}>
            {mic}
          </span>
        </div>
      </div>
      {!connected ? (
        <div className="rounded-osce-lg border border-osce-border bg-osce-surface p-4">
          <p className="text-osce-body font-semibold text-osce-ink-900">Reconnecting</p>
          <p className="mt-0.5 text-osce-meta text-b2c-text-muted">
            Your consultation can continue. We are holding the patient for you.
          </p>
        </div>
      ) : null}
      {lastMicrophoneError ? (
        <div className="rounded-osce-lg border border-osce-border bg-osce-surface p-4">
          <p className="text-osce-body font-semibold text-osce-ink-900">Microphone blocked</p>
          <p className="mt-0.5 text-osce-meta text-b2c-text-muted">
            Allow access in your browser&apos;s address bar, then try again.
          </p>
          <Button
            variant="secondary"
            size="sm"
            className="mt-3"
            onClick={() => localParticipant.setMicrophoneEnabled(true)}
          >
            Try again
          </Button>
        </div>
      ) : null}
    </div>
  );
}
