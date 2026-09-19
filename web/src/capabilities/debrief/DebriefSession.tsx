"use client";

import { useState } from "react";
import { HiMicrophone } from "react-icons/hi";
import { LuPhoneOff } from "react-icons/lu";
import { Alert, Button, Modal, ModalContent, ModalHelper, ModalTitle, Spinner } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { AgentTile, VoiceRoom, useMicPreflight } from "@/foundation/livekit";
import { useAttemptSession } from "@/capabilities/attempt-runner";
import { startDebrief } from "@/capabilities/debrief/api";

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
  onEnded,
}: {
  setId: string;
  entryId: string;
  onEnded?: (attemptId: string) => void;
}) {
  const session = useAttemptSession({
    start: () => startDebrief(setId, entryId),
    readingSeconds: 0,
    onEnded,
  });
  const mic = useMicPreflight(session.phase === "idle");

  if (session.phase === "ended") {
    return (
      <p className="p-6 text-center text-osce-body text-b2c-text-secondary">
        Debrief finished. Your summary appears in your debrief history once the tutor has written
        it up.
      </p>
    );
  }

  return (
    <div className="flex w-full flex-col gap-4 text-osce-body">
      {session.error && <Alert tone="danger">{errorMessage(session.error)}</Alert>}
      {mic.message && <Alert tone="warning">{mic.message}</Alert>}

      {session.phase === "idle" && (
        <div className="flex flex-col items-center gap-4 p-6 text-center">
          <p className="max-w-md text-b2c-text-muted">
            Athena has the consultation you just had. Talk it through — what you were thinking, what
            you would do differently — and she will write up what you agree.
          </p>
          <Button
            onClick={async () => {
              // Asked for from the click rather than on mount: a permission
              // prompt that appears on its own is the one people dismiss.
              if (mic.status !== "ready") await mic.request();
              await session.startConsultation();
            }}
          >
            <HiMicrophone className="h-4 w-4" aria-hidden /> Start talking
          </Button>
        </div>
      )}

      {(session.phase === "connecting" || session.phase === "ending") && (
        <div className="flex items-center justify-center gap-3 p-10 text-b2c-text-muted">
          <Spinner />
          {session.phase === "connecting" ? "Connecting you to Athena…" : "Wrapping up…"}
        </div>
      )}

      {session.phase === "live" && session.grant && (
        <VoiceRoom
          grant={session.grant}
          onConnected={session.attachRoom}
          onDisconnected={(unexpected) => {
            if (unexpected) void session.end();
          }}
        >
          <div className="flex flex-col items-center gap-5 py-4">
            <AgentTile
              name="Athena"
              detail="Your tutor, talking through the consultation you just had."
              className="w-full max-w-sm"
            />
            <Button variant="danger" onClick={() => void session.end()}>
              <LuPhoneOff className="h-4 w-4" aria-hidden /> End debrief
            </Button>
          </div>
        </VoiceRoom>
      )}

      {session.phase === "failed" && (
        <div className="flex justify-center p-6">
          <Button onClick={() => void session.startConsultation()}>Try again</Button>
        </div>
      )}
    </div>
  );
}

/**
 * The button that opens one, for a screen showing a station's feedback.
 *
 * The retiring modal offered a second option beside this — practising the same
 * case from the patient's side with the tutor as the doctor. That is a
 * practice session rather than a debrief on the platform and belongs with peer
 * practice; see `docs/port-gaps.md`.
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
