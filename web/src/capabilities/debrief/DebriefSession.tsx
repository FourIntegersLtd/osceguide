"use client";

import { useEffect, useState } from "react";
import { HiMicrophone } from "react-icons/hi";
import { Alert, ATHENA_IMAGE_SRC, Button, Modal, ModalContent, ModalHelper, ModalTitle } from "@/foundation/ui";
import { errorMessage, useToast } from "@/foundation/hooks";
import { VoiceRoom, useMicPreflight } from "@/foundation/livekit";
import { hasCode } from "@/foundation/platform-client";
import { useAttemptSession } from "@/capabilities/attempt-runner";
import { startDebrief, startAttemptDebrief } from "@/capabilities/debrief/api";

import LivekitIdleState from "@/foundation/livekit/LivekitIdleState";
import { DebriefVoiceStage } from "./DebriefVoiceStage";

/**
 * Talking a station through with the tutor, afterwards.
 *
 * A debrief is an attempt: same table, same room token, same worker contract —
 * so it runs on the shared session hook rather than on a voice service of its
 * own, which is what the retiring client gave it. There is no reading period
 * and no clock, because the thing being discussed has already happened.
 */
export function DebriefSession({
  setId,
  entryId,
  sourceAttemptId,
  onEnded,
}: {
  setId: string | null;
  entryId: string | null;
  sourceAttemptId?: string;
  onEnded?: (attemptId: string) => void;
}) {
  const toast = useToast();
  const [showSaved, setShowSaved] = useState(false);
  const session = useAttemptSession({
    start: () => setId && entryId
      ? startDebrief(setId, entryId)
      : sourceAttemptId ? startAttemptDebrief(sourceAttemptId)
        : Promise.reject(new Error("No consultation selected.")),
    readingSeconds: 0,
    onEnded,
  });
  const mic = useMicPreflight(session.phase === "idle");

  const endDebrief = async () => {
    setShowSaved(true);
    await session.end();
    window.setTimeout(() => setShowSaved(false), 5000);
  };

  useEffect(() => {
    if (!session.error) return;
    toast.show({
      tone: "error",
      title: "We couldn't start the debrief",
      message: hasCode(session.error, "nothing_to_debrief")
        ? "A debrief needs a recorded consultation for this station. Attempt the station first."
        : hasCode(session.error, "not_entitled")
          ? "Your completed consultation is available, but this account cannot start a voice debrief for this exam right now. Check your exam access or plan status."
        : errorMessage(session.error),
    });
  }, [session.error, toast]);

  const busy = session.phase === "connecting" || session.phase === "queued" || session.phase === "ending";
  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-osce-lg border border-b2c-border bg-osce-surface text-osce-body">
      <div className="flex min-h-[min(360px,42dvh)] flex-1 flex-col items-center justify-center bg-b2c-surface-muted px-5 py-6 lg:min-h-0">
        <div className="mx-auto flex w-full max-w-sm flex-col items-center">
          {session.error && <Alert tone="danger" className="mb-4">{errorMessage(session.error)}</Alert>}
          {mic.message && <Alert tone="warning" className="mb-4">{mic.message}</Alert>}
          {session.phase === "live" && session.grant ? (
            <VoiceRoom grant={session.grant} onConnected={session.attachRoom} onError={session.reportError}
              onDisconnected={(unexpected) => { if (unexpected) void session.end(); }}>
              <DebriefVoiceStage onEnd={() => void endDebrief()} />
            </VoiceRoom>
          ) : (
            <>
              <div className="mb-6 w-full">
                <LivekitIdleState avatar={{ kind: "image", src: ATHENA_IMAGE_SRC, alt: "Athena" }}
                  title="Athena Moderator" subtitle="Speak naturally to discuss your performance" />
              </div>
              <Button fullWidth disabled={busy || session.phase === "ended"} isLoading={busy}
                onClick={async () => {
                  if (mic.status !== "ready" && !await mic.request()) return;
                  await session.startConsultation();
                }}>
                {session.phase === "queued"
                  ? `Athena is busy. You are number ${session.queuePosition ?? 1} in line...`
                  : busy ? session.phase === "ending" ? "Wrapping up..." : "Connecting..." : "Start voice debrief"}
              </Button>
            </>
          )}
          {showSaved && session.phase === "ended" && <div className="mt-4 flex w-full items-center justify-center gap-2 rounded-osce-md border border-osce-success-border bg-osce-success-bg px-3 py-2 text-osce-success-text">
            <span className="text-osce-meta font-medium">Debrief ended. Your summary is being prepared.</span>
          </div>}
        </div>
      </div>
    </div>
  );
}

/**
 * The button that opens one, for a screen showing a station's feedback.
 *
 * Station feedback uses DebriefChooseModal to also offer patient roleplay.
 */
export function DebriefLauncher({ setId, entryId }: { setId: string; entryId: string }) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button
        type="button"
        onClick={() => setOpen(true)}
        className="w-full gap-2 sm:w-auto sm:min-w-[11rem]"
      >
        <HiMicrophone className="h-4 w-4" aria-hidden />
        <span>Start Debrief</span>
      </Button>

      {open && (
        <Modal width="min(1100px, 95vw)" height="fit-content" onClose={() => setOpen(false)}>
          <ModalContent className="flex flex-col space-y-3">
            <div className="text-center">
              <ModalTitle>Debrief Session</ModalTitle>
              <ModalHelper className="mx-auto max-w-md">
                Review your consultation with Athena and get detailed feedback on your performance.
              </ModalHelper>
            </div>
            <DebriefSession setId={setId} entryId={entryId} />
          </ModalContent>
        </Modal>
      )}
    </>
  );
}
