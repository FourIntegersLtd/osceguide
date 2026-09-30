"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AsyncBoundary, Button } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities/SurfaceContext";
import { readPracticeSession } from "../api";
import { PeerAiFeedback } from "./PeerAiFeedback";
import { SessionFeedback } from "./SessionFeedback";

/**
 * Where a practice session ends: "Session Completed", the rating form for the
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
      <div className="mx-auto max-w-7xl px-3 py-4 sm:px-4 sm:py-6">
        <div className="mb-4 text-center">
          <h2 className="mb-1 text-osce-body font-bold text-osce-ink-900">Session Completed</h2>
          <p className="text-osce-body text-b2c-text-secondary">Thank you for participating in the practice session!</p>
        </div>
        <AsyncBoundary state={loaded}>
          {(session) => (
            <div className="text-center">
              <PeerAiFeedback session={session} />
              {!feedbackSubmitted ? (
                <SessionFeedback sessionId={session.id} onDone={() => setFeedbackSubmitted(true)} />
              ) : (
                <>
                  <div className="mb-4 inline-block rounded-lg border border-osce-success-border bg-osce-success-bg px-4 py-3 text-osce-success-text">
                    <p className="text-osce-body font-semibold">✓ Thank you for your feedback!</p>
                  </div>
                  <div>
                    <Button type="button" variant="primary" size="md" onClick={() => router.push(hrefFor(""))}>
                      Return to Dashboard
                    </Button>
                  </div>
                </>
              )}
            </div>
          )}
        </AsyncBoundary>
      </div>
    </div>
  );
}
