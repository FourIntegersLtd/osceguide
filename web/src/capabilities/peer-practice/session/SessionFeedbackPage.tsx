"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Alert, AsyncBoundary, Button } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities/SurfaceContext";
import { readPracticeSession } from "../api";
import { PeerAiFeedback } from "./PeerAiFeedback";
import { SessionFeedback } from "./SessionFeedback";
import { B2CHero } from "@/foundation/ui/B2CHero";

/**
 * Where a practice session ends: "Session completed", the rating form for the
 * partner, and — for the doctor — the notice that the AI feedback is on its
 * way. The session is read once so the page knows the caller's role; the
 * retiring route took it from `?role=` instead.
 */
export function PeerSessionFeedbackPage({ sessionId }: { sessionId: string }) {
  const loaded = useAsync((signal) => readPracticeSession(sessionId, signal), [sessionId]);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const router = useRouter();
  const { hrefFor } = useSurface();

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl space-y-6 px-3 py-4 sm:px-4 sm:py-6">
        <B2CHero
          eyebrow="Session completed"
          title="Thank you for practising"
          action={
            feedbackSubmitted ? (
              <Button type="button" onClick={() => router.push(hrefFor(""))}>
                Back to dashboard
              </Button>
            ) : null
          }
        >
          Rate your colleague below, then head back when you are ready.
        </B2CHero>
        <AsyncBoundary state={loaded}>
          {(session) => (
            <div className="space-y-6">
              <PeerAiFeedback session={session} />
              {!feedbackSubmitted ? (
                <SessionFeedback sessionId={session.id} onDone={() => setFeedbackSubmitted(true)} />
              ) : (
                <Alert tone="success">Thank you for your feedback.</Alert>
              )}
            </div>
          )}
        </AsyncBoundary>
      </div>
    </div>
  );
}
