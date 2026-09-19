"use client";

import { useEffect, useState } from "react";
import { Modal, Spinner } from "@/foundation/ui";
import { readResults } from "@/capabilities/attempt-runner";

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
  examCode,
  onReady,
  onSkip,
}: {
  isOpen: boolean;
  attemptId: string | null;
  examCode: string;
  onReady: () => void;
  onSkip: () => void;
}) {
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
    <Modal onClose={onSkip} width="min(95vw, 36rem)" height="fit-content">
      <div className="space-y-5 p-6 text-center">
        <div className="flex justify-center">
          <Spinner />
        </div>
        <div className="space-y-1.5">
          <h2 className="text-osce-h3 font-semibold text-osce-ink-900">
            {givenUp ? "Marking is taking longer than usual" : "Marking your consultation"}
          </h2>
          <p className="text-osce-body text-b2c-text-muted">
            {givenUp
              ? "Your attempt is safe. Your feedback will be on this station when it is ready."
              : "This usually takes about a minute. You can wait here or carry on."}
          </p>
        </div>

        {!givenUp && examCode === "sca" && <ConsultationTips />}

        <button
          type="button"
          onClick={onSkip}
          className="text-osce-body text-osce-accent underline underline-offset-2 hover:text-osce-accent-hover"
        >
          Continue to your session summary
        </button>
      </div>
    </Modal>
  );
}

/**
 * Something worth reading while the marking runs.
 *
 * SCA only, as in the old client: these are the RCGP domains' own vocabulary
 * and would be wrong for PLAB or CASC.
 */
function ConsultationTips() {
  return (
    <ul className="space-y-2 rounded-2xl border border-osce-tone-tip-border bg-osce-tone-tip-bg p-4 text-left text-osce-body text-osce-tone-tip-body">
      <li>Ask about ideas, concerns and expectations early, and respond to what you hear.</li>
      <li>Say the safety net out loud: what should make them come back, and how soon.</li>
      <li>Check understanding by asking them to say the plan back, not by asking &ldquo;is that OK?&rdquo;.</li>
      <li>Leave time to agree the plan together rather than announcing it at the end.</li>
    </ul>
  );
}
