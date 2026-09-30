"use client";

import { useEffect, useState } from "react";
import { Modal, ModalCallout } from "@/foundation/ui";
import { readResults } from "@/capabilities/attempt-runner";
import { GeneratingFeedback } from "@/capabilities/station-runner/GeneratingFeedback";
import { useCurrentExam } from "@/foundation/session";
import Tips from "./tips/Tips";

const MAX_TRIES = 10;

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
export function MarkingModal({
  isOpen,
  attemptId,
  onReady,
  onSkip,
}: {
  isOpen: boolean;
  attemptId: string | null;
  onReady: () => void;
  onSkip: () => void;
}) {
  const { settings } = useCurrentExam();
  const [tries, setTries] = useState(0);

  useEffect(() => {
    if (!isOpen || !attemptId || tries >= MAX_TRIES) return;
    let live = true;

    // Backs off: a long consultation takes longer to mark than a short one,
    // and asking every second buys nothing.
    const delay = Math.min(30_000, 3_000 * (tries + 1));
    const timer = window.setTimeout(() => {
      void readResults(attemptId)
        .then((results) => {
          if (!live) return;
          if (results.length > 0) onReady();
          else setTries((n) => n + 1);
        })
        .catch(() => {
          if (live) setTries((n) => n + 1);
        });
    }, delay);

    return () => {
      live = false;
      window.clearTimeout(timer);
    };
  }, [isOpen, attemptId, tries, onReady]);

  useEffect(() => {
    if (isOpen) setTries(0);
  }, [isOpen]);

  if (!isOpen) return null;

  const givenUp = tries >= MAX_TRIES;

  return (
    <Modal
      onClose={onSkip}
      width="600px"
      height="fit-content"
      title={givenUp ? undefined : "Marking your consultation"}
    >
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

      {givenUp ? (
        <div className="space-y-3 p-6 text-center">
          <h2 className="text-osce-h3 font-semibold text-osce-ink-900">
            Marking is taking longer than usual
          </h2>
          <p className="text-osce-body text-b2c-text-muted">
            Your attempt is safe. Your feedback will be on this station when it is ready.
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
