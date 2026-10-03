"use client";

import { useEffect, useState } from "react";
import { HiMicrophone } from "react-icons/hi";
import { Alert, ATHENA_IMAGE_SRC, Button, Modal, ModalContent, ModalHelper, ModalTitle, productTokens } from "@/foundation/ui";
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
  onDone,
}: {
  setId: string | null;
  entryId: string | null;
  sourceAttemptId?: string;
  onEnded?: (attemptId: string) => void;
  /** Where "Done" goes once the debrief has ended; without it the ended state has no button. */
  onDone?: () => void;
}) {
  const toast = useToast();
  const session = useAttemptSession({
    start: () => setId && entryId
      ? startDebrief(setId, entryId)
      : sourceAttemptId ? startAttemptDebrief(sourceAttemptId)
        : Promise.reject(new Error("No consultation selected.")),
    readingSeconds: 0,
    onEnded,
  });
  const mic = useMicPreflight(session.phase === "idle");

  const endDebrief = () => session.end();

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
    <div data-skin={session.phase === "live" ? "room" : undefined}
      className="grid h-full min-h-0 grid-cols-1 gap-3 overflow-y-auto rounded-osce-2xl bg-osce-canvas p-3 text-osce-body lg:grid-cols-[1.4fr_1fr]">
      <section className="flex min-h-[min(360px,42dvh)] flex-col items-center justify-center rounded-osce-lg border border-osce-border bg-osce-surface px-5 py-6">
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
                  title="Athena" subtitle="Speak naturally to discuss your performance" />
              </div>
              {session.phase === "ended" ? (
                // Ended is final: offering "Start voice debrief" again (disabled) read as if nothing
                // had happened (staging, 2026-10-03).
                <div className="flex w-full flex-col items-center gap-3">
                  <Alert tone="success" className="w-full">
                    Debrief ended. Athena is writing your summary; it will appear in Debrief History.
                  </Alert>
                  {onDone ? <Button fullWidth onClick={onDone}>Done</Button> : null}
                </div>
              ) : (
                <Button fullWidth disabled={busy} isLoading={busy}
                  onClick={async () => {
                    if (mic.status !== "ready" && !await mic.request()) return;
                    await session.startConsultation();
                  }}>
                  {session.phase === "queued"
                    ? `Athena is busy. You are number ${session.queuePosition ?? 1} in line...`
                    : busy ? session.phase === "ending" ? "Wrapping up..." : "Connecting..." : "Start voice debrief"}
                </Button>
              )}
            </>
          )}
        </div>
      </section>
      <TalkingPoints />
    </div>
  );
}

const TALKING_POINTS = [
  { eyebrow: "Live analysis", text: "Athena has your transcript and marks open." },
  { eyebrow: "Targeted tips", text: "Ask why a point lost the mark, and what would have earned it." },
  { eyebrow: "Active practice", text: "Rehearse your plan out loud and Athena will respond." },
];

function TalkingPoints() {
  return (
    <section className="rounded-osce-lg border border-osce-border bg-osce-surface">
      <h2 className="px-5 pb-1 pt-[18px] text-osce-subheading font-semibold text-osce-ink-900">Talking points</h2>
      <ul className="divide-y divide-osce-border-light px-5 pb-3">
        {TALKING_POINTS.map((point) => (
          <li key={point.eyebrow} className="py-3">
            <p className={productTokens.b2cMonoEyebrow}>{point.eyebrow}</p>
            <p className="mt-1 text-osce-meta leading-relaxed text-b2c-text-muted">{point.text}</p>
          </li>
        ))}
      </ul>
    </section>
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
        <span>Start debrief</span>
      </Button>

      {open && (
        <Modal width="min(1100px, 95vw)" height="fit-content" onClose={() => setOpen(false)}>
          <ModalContent className="flex flex-col space-y-3">
            <div className="text-center">
              <ModalTitle>Debrief session</ModalTitle>
              <ModalHelper className="mx-auto max-w-md">
                Review your consultation with Athena and get detailed feedback on your performance.
              </ModalHelper>
            </div>
            <DebriefSession setId={setId} entryId={entryId} onDone={() => setOpen(false)} />
          </ModalContent>
        </Modal>
      )}
    </>
  );
}
