"use client";

import { useState } from "react";
import { HiOutlinePhone, HiOutlineUser } from "react-icons/hi2";
import { LuPhoneOff } from "react-icons/lu";
import { Alert, Button, ConfirmModal, Spinner, cn } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { AgentTile, VoiceRoom, useMicPreflight, type MicPreflight } from "@/foundation/livekit";
import type { AttemptSession } from "@/capabilities/attempt-runner/useAttemptSession";

export interface PatientIdentity {
  name: string;
  detail?: string | null;
}

/**
 * The left-hand column: who you are about to speak to, and the one button.
 *
 * Before connecting it is the retiring client's preflight — a monogram, the
 * patient's name and biodata, how long the consultation runs, and whether the
 * microphone is working. During the call it is the patient's tile and a single
 * red End button behind a confirmation, because ending early by a misclick is
 * the one mistake here that cannot be undone.
 *
 * Everything it knows about the attempt comes from `session`, so the same
 * panel serves a consumer mock, an institution's circuit and a peer session.
 */
export function ConsultationPanel({
  session,
  patient,
  durationSeconds,
  startLabel = "Start Consultation",
  disabledReason,
}: {
  session: AttemptSession;
  patient: PatientIdentity;
  durationSeconds: number;
  startLabel?: string;
  /** Set in review, where the patient is not called again. */
  disabledReason?: string | null;
}) {
  const mic = useMicPreflight(session.phase === "idle" || session.phase === "reading");
  const [confirmingEnd, setConfirmingEnd] = useState(false);

  const start = async () => {
    if (mic.status !== "ready") await mic.request();
    await session.startConsultation();
  };

  return (
    <div className="flex h-full flex-col justify-between gap-4">
      {session.error && <Alert tone="danger">{errorMessage(session.error)}</Alert>}

      {session.phase === "live" && session.grant ? (
        <VoiceRoom
          grant={session.grant}
          onConnected={session.attachRoom}
          onDisconnected={(unexpected) => {
            if (unexpected) void session.end();
          }}
        >
          <div className="flex flex-col items-center gap-5">
            <AgentTile name={patient.name} detail={patient.detail} className="w-full" />
            <Button variant="danger" onClick={() => setConfirmingEnd(true)} className="w-full">
              <LuPhoneOff className="h-4 w-4" aria-hidden /> End Consultation
            </Button>
          </div>
        </VoiceRoom>
      ) : session.phase === "connecting" ? (
        <Connecting />
      ) : session.phase === "ending" ? (
        <div className="flex items-center justify-center gap-3 py-8 text-osce-body text-b2c-text-muted">
          <Spinner /> Wrapping up…
        </div>
      ) : (
        <>
          <Preflight patient={patient} durationSeconds={durationSeconds} mic={mic} />
          <div className="space-y-2">
            {disabledReason ? (
              <p className="text-center text-osce-meta text-b2c-text-muted">{disabledReason}</p>
            ) : (
              <Button variant="primary" size="md" onClick={() => void start()} className="w-full">
                <HiOutlinePhone className="h-4 w-4" aria-hidden />
                {session.phase === "failed" ? "Try again" : startLabel}
              </Button>
            )}
          </div>
        </>
      )}

      <ConfirmModal
        isOpen={confirmingEnd}
        title="End this consultation?"
        message="Your consultation will be sent for marking. You cannot go back into the room."
        confirmText="End Consultation"
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

function Connecting() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-8">
      <Spinner />
      <p className="text-osce-body text-b2c-text-muted">Connecting you to the patient…</p>
    </div>
  );
}

/** Who you are about to speak to, and whether your microphone works. */
function Preflight({
  patient,
  durationSeconds,
  mic,
}: {
  patient: PatientIdentity;
  durationSeconds: number;
  mic: MicPreflight;
}) {
  return (
    <div className="flex flex-col items-center gap-4 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-accent-subtle text-lg font-semibold text-accent">
        {initials(patient.name)}
      </div>
      <div>
        <p className="text-osce-body font-medium text-osce-ink-900">{patient.name}</p>
        {patient.detail && (
          <p className="mt-0.5 text-osce-meta text-b2c-text-muted">{patient.detail}</p>
        )}
      </div>

      <p className="text-osce-meta text-b2c-text-muted">
        You have {Math.round(durationSeconds / 60)} minutes with this patient.
      </p>

      <MicCheck mic={mic} />
    </div>
  );
}

/**
 * Whether the microphone is working, said before it matters.
 *
 * The one thing that turns a consultation into a wasted attempt: finding out
 * the microphone is blocked after the clock has started.
 */
function MicCheck({ mic }: { mic: MicPreflight }) {
  const tone =
    mic.status === "ready"
      ? "border-osce-tone-safety-border bg-osce-tone-safety-bg text-osce-tone-safety-text"
      : mic.status === "checking"
        ? "border-b2c-border bg-b2c-surface-muted text-b2c-text-muted"
        : "border-osce-tone-history-border bg-osce-tone-history-bg text-osce-tone-history-text";

  return (
    <div className={cn("w-full rounded-xl border px-3 py-2 text-osce-meta", tone)}>
      <span className="flex items-center justify-center gap-1.5">
        <HiOutlineUser className="h-3.5 w-3.5 shrink-0" aria-hidden />
        {mic.status === "ready"
          ? "Microphone ready"
          : mic.status === "checking"
            ? "Checking your microphone…"
            : (mic.message ?? "We could not reach your microphone")}
      </span>
    </div>
  );
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}
