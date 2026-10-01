"use client";

import { useState } from "react";
import {
  BarVisualizer,
  useConnectionState,
  useVoiceAssistant,
} from "@livekit/components-react";
import { ConnectionState } from "livekit-client";
import { HiOutlineMicrophone, HiOutlinePhoneXMark } from "react-icons/hi2";
import { Alert, Button, ConfirmModal, Spinner, cn, productTokens } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { VoiceRoom, useMicPreflight } from "@/foundation/livekit";
import LivekitIdleState, { LivekitAvatarMotif } from "@/foundation/livekit/LivekitIdleState";
import { ConsultationConnectionStatus } from "@/capabilities/attempt-runner/consultation/ConsultationConnectionStatus";
import { AGENT_STATE_LABEL } from "@/foundation/livekit/types";
import type { AttemptSession } from "@/capabilities/attempt-runner/useAttemptSession";
import type { ConsultationPatient } from "@/capabilities/attempt-runner/consultation/patientIdentity";
import { WaitingInLine } from "@/capabilities/attempt-runner/WaitingInLine";

const { b2cLivekitEndButton } = productTokens;

export interface ConsultationPanelProps {
  session: AttemptSession;
  patient: ConsultationPatient;
  durationSeconds: number;
  startLabel?: string;
  disabledReason?: string | null;
}

/**
 * Left-hand consultation column — layout matches legacy `LivekitConsultationService`:
 * patient monogram and visualiser above; Connecting… or End Consultation below.
 */
export function ConsultationPanel({
  session,
  patient,
  durationSeconds,
  startLabel = "Start Consultation",
  disabledReason,
}: ConsultationPanelProps) {
  const mic = useMicPreflight(session.phase === "idle" || session.phase === "reading");
  const [confirmingEnd, setConfirmingEnd] = useState(false);

  const start = async () => {
    if (mic.status !== "ready" && !await mic.request()) return;
    await session.startConsultation();
  };

  return (
    <div className="flex h-full min-h-[min(340px,48vh)] flex-1 flex-col justify-between gap-4">
      {session.error && <Alert tone="danger">{errorMessage(session.error)}</Alert>}
      {mic.message && <Alert tone="warning">{mic.message}</Alert>}

      {session.phase === "live" && session.grant ? (
        <VoiceRoom
          // Bottom-aligned as the legacy room: the stage sits just above the controls.
          className="flex min-h-0 w-full flex-1 flex-col justify-end gap-4"
          grant={session.grant}
          onConnected={session.attachRoom}
          onError={session.reportError}
          onDisconnected={(unexpected) => {
            if (unexpected) void session.end();
          }}
        >
          <ConsultationLiveStage
            initials={patient.initials}
            onRequestEnd={() => setConfirmingEnd(true)}
          />
        </VoiceRoom>
      ) : session.phase === "connecting" ? (
        <div className="flex flex-col items-center justify-center gap-3 py-8">
          <Spinner />
          <p className="text-osce-body text-b2c-text-muted">Connecting you to the patient…</p>
        </div>
      ) : session.phase === "queued" ? (
        <WaitingInLine position={session.queuePosition} onLeave={session.leaveQueue} />
      ) : session.phase === "ending" ? (
        <div className="flex items-center justify-center gap-3 py-8 text-osce-body text-b2c-text-muted">
          <Spinner /> Wrapping up…
        </div>
      ) : (
        <>
          <LivekitIdleState
            avatar={{ kind: "monogram", initials: patient.initials }}
            durationMinutes={Math.round(durationSeconds / 60)}
            showReadiness={!disabledReason && session.phase !== "ended"}
          />
          <div className="space-y-2">
            {disabledReason || session.phase === "ended" ? (
              <>
                <Button fullWidth disabled className="gap-2"><HiOutlineMicrophone className="h-4 w-4" aria-hidden />Start Consultation</Button>
                <p className="text-center text-osce-caption text-b2c-text-muted sm:text-osce-meta">{disabledReason ?? "Consultation completed"}</p>
              </>
            ) : (
              <Button variant="primary" size="md" onClick={() => void start()} className="w-full gap-2">
                <HiOutlineMicrophone className="h-4 w-4" aria-hidden />
                {session.phase === "failed" ? "Try again" : startLabel}
              </Button>
            )}
          </div>
        </>
      )}

      <ConfirmModal
        isOpen={confirmingEnd}
        title="End consultation now?"
        message="Your feedback will be based on what you've said so far. You can't resume once it ends."
        confirmText="End consultation"
        cancelText="Keep going"
        tone="danger"
        onConfirm={() => {
          setConfirmingEnd(false);
          void session.end();
        }}
        onCancel={() => setConfirmingEnd(false)}
      />
    </div>
  );
}

/** Visualiser + controls; must render inside `VoiceRoom`. */
function ConsultationLiveStage({
  initials,
  onRequestEnd,
}: {
  initials: string;
  onRequestEnd: () => void;
}) {
  const { state, audioTrack } = useVoiceAssistant();
  const connectionState = useConnectionState();

  const isRoomReconnecting =
    connectionState === ConnectionState.Reconnecting ||
    connectionState === ConnectionState.SignalReconnecting;
  const isRoomConnecting = connectionState === ConnectionState.Connecting;
  // Match legacy consultation controls: disabled Connecting… until the room
  // has joined; agent status copy lives in the line above the button.
  const isStarting = isRoomConnecting || isRoomReconnecting;

  const agentLabel =
    state === "disconnected" && connectionState !== ConnectionState.Connected
      ? ""
      : (AGENT_STATE_LABEL[state] ?? state);

  return (
    <div className="flex w-full shrink-0 flex-col gap-4">
      <div className="relative flex w-full shrink-0 flex-col items-center justify-center overflow-hidden py-2">
        <div className="z-10 w-full max-w-md px-2">
          {/* The same ringed monogram as before the call starts; no biodata line. */}
          <LivekitAvatarMotif avatar={{ kind: "monogram", initials }} className="mx-auto mb-2" />
          <div className="h-28 w-full lg:h-20">
            <BarVisualizer
              state={state}
              barCount={5}
              trackRef={audioTrack}
              style={{
                height: "100%",
                opacity: state === "disconnected" ? 0.5 : 1,
                transition: "all 0.3s ease",
              }}
            />
          </div>
          <p
            role="status"
            aria-live="polite"
            className="mt-2 text-center text-osce-body font-extralight tracking-wide text-b2c-text-secondary"
          >
            {agentLabel}
          </p>
        </div>
      </div>

      <div className="w-full px-2">
        <ConsultationConnectionStatus />
        {isStarting ? (
          <Button
            type="button"
            variant="primary"
            size="md"
            fullWidth
            disabled
            isLoading
            aria-busy
            className="gap-2"
          >
            <span>Connecting…</span>
          </Button>
        ) : (
          <button
            type="button"
            className={cn(b2cLivekitEndButton, "w-full gap-2")}
            onClick={onRequestEnd}
          >
            <HiOutlinePhoneXMark className="h-4 w-4 sm:h-5 sm:w-5" aria-hidden />
            <span className="text-osce-caption sm:text-osce-body">End Consultation</span>
          </button>
        )}
      </div>
    </div>
  );
}
