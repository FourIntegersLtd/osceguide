"use client";

import { useEffect, useRef, useState } from "react";
import { Alert, Button, Modal, ModalCallout } from "@/foundation/ui";
import { useMeEvents } from "@/foundation/hooks";
import { readAttempt, readResults } from "@/capabilities/attempt-runner";
import { GeneratingFeedback } from "@/capabilities/station-runner/GeneratingFeedback";
import { watchMarking, type MarkingWait } from "@/capabilities/station-runner/markingWait";
import { useCurrentExam } from "@/foundation/session";
import Tips from "./tips/Tips";

/**
 * "Marking your consultation" — the wait between hanging up and the feedback.
 *
 * Scoring is a background job of a minute or two, and the retiring client
 * filled that time rather than showing a spinner: consultation tips on SCA, a
 * short explanation of what is happening elsewhere. Both had the same escape
 * hatch, and it stays, because a marking that is taking longer than usual must
 * never trap somebody on a modal.
 *
 * The attempt is safe either way — it is recorded server-side the moment the
 * transcript lands — so leaving costs nothing but the automatic jump to the
 * feedback tab.
 */
export function MarkingModal(props: {
  isOpen: boolean;
  attemptId: string | null;
  onReady: () => void;
  onSkip: () => void;
}) {
  // The wait (and its `/me/events` connection) exists only while the modal is open.
  if (!props.isOpen) return null;
  return <OpenMarkingModal {...props} />;
}

function OpenMarkingModal({
  attemptId,
  onReady,
  onSkip,
}: {
  attemptId: string | null;
  onReady: () => void;
  onSkip: () => void;
}) {
  const { settings } = useCurrentExam();
  const [phase, setPhase] = useState<"waiting" | "slow" | "failed">("waiting");
  const slow = phase === "slow";
  const failed = phase === "failed";
  const [attempts, setAttempts] = useState(0);
  const waitRef = useRef<MarkingWait | null>(null);
  const onReadyRef = useRef(onReady);
  useEffect(() => {
    onReadyRef.current = onReady;
  }, [onReady]);

  useEffect(() => {
    if (!attemptId) return;
    const wait = watchMarking({
      isMarked: async () => (await readResults(attemptId)).length > 0,
      onReady: () => onReadyRef.current(),
      failure: {
        check: async () => (await readAttempt(attemptId)).status === "failed",
        onFailed: () => setPhase("failed"),
      },
      onSlow: () => setPhase((now) => (now === "failed" ? now : "slow")),
    });
    waitRef.current = wait;
    return () => {
      wait.stop();
      waitRef.current = null;
    };
  }, [attemptId, attempts]);

  // The scoring job announces `attempt` when it stores a result; `resync` comes when the
  // stream (re)connects or the tab is shown again, which covers an event sent while no
  // stream was open — before this modal mounted, or while an API restart had dropped it.
  useMeEvents(["attempt"], (event) => {
    if (event.name === "resync" || event.data.attempt_id === attemptId) waitRef.current?.wake();
  });

  return (
    <Modal
      onClose={onSkip}
      width="600px"
      height="fit-content"
      title={slow ? undefined : "Marking your consultation"}
    >
      {!failed && (
      <ModalCallout className="mb-4 mt-0">
        Marking usually takes one to three minutes. You don&apos;t have to wait here:{" "}
        <button
          type="button"
          onClick={onSkip}
          className="font-semibold text-osce-accent underline underline-offset-2 hover:text-osce-accent-hover"
        >
          continue to your session summary
        </button>{" "}
        and we&apos;ll let you know the moment your feedback is ready.
      </ModalCallout>
      )}

      {failed ? (
        <div className="space-y-3 p-6 text-center">
          <h2 className="text-osce-h3 font-semibold text-osce-ink-900">
            We could not mark this consultation
          </h2>
          <Alert tone="danger">
            Marking failed, so there is no feedback for this attempt. Check again in a moment, or
            continue to your session summary and start the station again. If it keeps happening,
            contact support and quote the station and the time.
          </Alert>
          <div className="flex justify-center gap-2">
            <Button
              variant="secondary"
              onClick={() => {
                setPhase("waiting");
                setAttempts((n) => n + 1);
              }}
            >
              Check again
            </Button>
            <Button variant="commit" onClick={onSkip}>
              Continue to session summary
            </Button>
          </div>
        </div>
      ) : slow ? (
        <div className="space-y-3 p-6 text-center">
          <h2 className="text-osce-h3 font-semibold text-osce-ink-900">
            Marking is taking longer than usual
          </h2>
          <p className="text-osce-body text-b2c-text-muted">
            Your attempt is safe. This page will show your feedback as soon as it is ready.
          </p>
        </div>
      ) : settings.show_tips_while_marking ? (
        <Tips duration={120} />
      ) : (
        <GeneratingFeedback />
      )}
    </Modal>
  );
}
