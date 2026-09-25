"use client";

import { useEffect, useState } from "react";
import { HiOutlineSparkles } from "react-icons/hi2";
import { Alert, LoadingSpinner, productTokens } from "@/foundation/ui";
import { AttemptFeedback } from "@/capabilities/feedback";
import { readPracticeSession, type PracticeSession } from "../api";

const { b2cCard } = productTokens;

/** How often the finished screen asks whether the marking has landed. */
const POLL_MS = 5000;

/**
 * The doctor's marked feedback for a session practised with a person.
 *
 * The consultation was recorded, transcribed and turned into an attempt by a
 * background job, so "not yet" is the ordinary state of this panel for the
 * first minute or two rather than a failure. Once the session names an
 * attempt, the ordinary feedback screen takes over — a peer attempt is marked
 * by the same engine against the same rubric as a mock, and showing it through
 * a second renderer is how two clients come to disagree about what a grade
 * means.
 *
 * Only the doctor is marked. The backend withholds the attempt id from the
 * patient, so this panel is simply never given one.
 */
export function PeerAiFeedback({ session }: { session: PracticeSession }) {
  const state = usePeerFeedback(session);

  if (state.attemptId) {
    return (
      <section className="space-y-4">
        <Heading />
        <AttemptFeedback attemptId={state.attemptId} />
      </section>
    );
  }

  if (state.failed) {
    return (
      <section className="space-y-3">
        <Heading />
        <Alert tone="warning">
          We could not turn this consultation into feedback. The recording may not have reached us.
          Your session and your partner&apos;s rating are unaffected.
        </Alert>
      </section>
    );
  }

  if (state.pending) {
    return (
      <section className={`${b2cCard} space-y-3 p-6 text-center`}>
        <Heading />
        <LoadingSpinner />
        <p className="text-sm text-ink-muted">
          We are listening back to your consultation and marking it. This usually takes a couple of
          minutes — you can leave this page and find it again in your feedback.
        </p>
      </section>
    );
  }

  return null;
}

function Heading() {
  return (
    <h2 className="flex items-center gap-2 font-semibold text-ink">
      <HiOutlineSparkles className="h-5 w-5 text-accent" aria-hidden />
      AI feedback on your consultation
    </h2>
  );
}

/**
 * Watches the session until its feedback is somewhere final.
 *
 * Polling rather than the session stream because this screen is only reached
 * once the session is over, and the stream is closed by then.
 */
function usePeerFeedback(initial: PracticeSession) {
  const [latest, setLatest] = useState(initial);
  const attemptId = latest.doctor_attempt_id ?? null;
  const feedbackState = latest.feedback_state;
  const pending = !attemptId && feedbackState === "pending";
  const sessionId = initial.id;

  useEffect(() => {
    if (!pending) return;
    let live = true;
    const timer = window.setInterval(() => {
      void readPracticeSession(sessionId)
        .then((next) => {
          if (live) setLatest(next);
        })
        .catch(() => {
          // A transient read must not replace the wait with an error.
        });
    }, POLL_MS);
    return () => {
      live = false;
      window.clearInterval(timer);
    };
  }, [pending, sessionId]);

  return { attemptId, pending, failed: feedbackState === "failed" };
}
