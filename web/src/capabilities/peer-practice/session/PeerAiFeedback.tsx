"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { LuBot } from "react-icons/lu";
import { HiOutlineCheckCircle, HiOutlineClock, HiOutlineDocumentText } from "react-icons/hi2";
import {
  Alert,
  Modal,
  ModalContent,
  ModalFooterActions,
  ModalLead,
  ModalList,
  ModalListRow,
  ModalPrimaryButton,
  ModalSecondaryButton,
  ModalSection,
} from "@/foundation/ui";
import { useSurface } from "@/capabilities/SurfaceContext";
import { useMeEvents } from "@/foundation/hooks";
import { readPracticeSession, type PracticeSession } from "../api";

/**
 * The doctor's side of the AI feedback, on the page a session ends on.
 *
 * The consultation is recorded, transcribed and marked by a background job,
 * so for the first minute or two "not ready" is the ordinary state. The page
 * says so, watches the session, and when the marking lands says so in the
 * same dialog the retiring client showed. Only the doctor is marked: the
 * backend withholds the attempt from the patient, so a patient sees nothing.
 */
export function PeerAiFeedback({ session }: { session: PracticeSession }) {
  const { attemptId, failed } = usePeerFeedback(session);
  const [dismissed, setDismissed] = useState(false);
  const router = useRouter();
  const { hrefFor } = useSurface();

  if (session.my_role !== "doctor") return null;

  if (failed) {
    // Not in the retiring client, which stopped polling without a word; a
    // failure must not read as "still coming".
    return (
      <div className="mx-auto mb-4 max-w-2xl text-left">
        <Alert tone="warning">
          We could not turn this consultation into feedback. The recording may not have reached us. Your session and
          your partner&apos;s rating are unaffected.
        </Alert>
      </div>
    );
  }

  if (attemptId) {
    if (dismissed) return null;
    return (
      <Modal width="550px" height="fit-content" onClose={() => setDismissed(true)}>
        <ModalContent>
          <ModalLead
            title="Your AI feedback is ready"
            description="Your session transcript and AI-generated feedback have been processed successfully."
            icon={<HiOutlineCheckCircle className="h-5 w-5" />}
            iconTone="competent"
          />
          <ModalSection title="What's available">
            <ModalList>
              <ModalListRow
                icon={<HiOutlineDocumentText className="h-3.5 w-3.5" />}
                title="Complete transcript"
                description="Review your full conversation with timestamps and speaker labels"
              />
              <ModalListRow
                icon={<LuBot className="h-3.5 w-3.5" />}
                iconTone="violet"
                title="AI feedback & analysis"
                description="Detailed skill scores, personalised insights, and improvement recommendations"
              />
            </ModalList>
          </ModalSection>
          <ModalFooterActions>
            <ModalSecondaryButton onClick={() => setDismissed(true)}>Dismiss</ModalSecondaryButton>
            <ModalPrimaryButton onClick={() => router.push(hrefFor("/mocks/list"))}>
              View my mocks &amp; feedback
            </ModalPrimaryButton>
          </ModalFooterActions>
        </ModalContent>
      </Modal>
    );
  }

  return (
    <div className="mx-auto mb-4 max-w-2xl rounded-lg border border-osce-accent-subtle bg-osce-accent-muted p-3 text-left sm:p-4">
      <div className="flex items-start gap-2 sm:gap-3">
        <div className="mt-0.5 flex-shrink-0">
          <LuBot className="h-4 w-4 text-osce-accent sm:h-5 sm:w-5" />
        </div>
        <div className="flex-1">
          <h4 className="mb-1 text-osce-body font-semibold text-osce-ink-900">AI Transcript &amp; Feedback Processing</h4>
          <p className="mb-2 text-osce-body text-osce-accent-hover">
            Your session transcript and AI-generated feedback are being processed and will be ready in approximately 2
            minutes.
          </p>
          <div className="flex items-center gap-1.5 text-osce-body text-osce-accent-hover">
            <HiOutlineClock className="h-3 w-3 sm:h-4 sm:w-4" />
            <span>
              We&apos;ll notify you once they&apos;re ready - feel free to continue using the app in the meantime
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Watches the session until its feedback is somewhere final.
 *
 * `build_feedback` publishes `practice.session_updated` to the doctor once marking
 * lands or fails, on this user's own event stream — replacing the retiring client's
 * timed re-checks with a read triggered by the event that actually says something
 * changed (and, as a backstop, by a `resync` on reconnect or the tab returning).
 */
function usePeerFeedback(initial: PracticeSession) {
  const [latest, setLatest] = useState(initial);
  const attemptId = latest.doctor_attempt_id ?? null;
  const failed = latest.feedback_state === "failed";
  const waiting = initial.my_role === "doctor" && !attemptId && !failed;
  const sessionId = initial.id;

  const look = useCallback(() => {
    void readPracticeSession(sessionId)
      .then((next) => setLatest(next))
      .catch(() => {
        // A transient read must not replace the wait with an error.
      });
  }, [sessionId]);

  useMeEvents(
    waiting ? ["practice.session_updated"] : null,
    useCallback(
      (event) => {
        if (event.name === "resync" || event.data.session_id === sessionId) look();
      },
      [sessionId, look],
    ),
  );

  return { attemptId, failed };
}
