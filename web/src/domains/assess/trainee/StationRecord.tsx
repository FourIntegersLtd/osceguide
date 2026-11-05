"use client";

import { AsyncBoundary, b2bTokens } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { AttemptFeedback, TranscriptView, readTranscript } from "@/capabilities/feedback";

/**
 * One station, read back: what was said, and how it was marked.
 *
 * The retiring arm called this the consultation record and built it from a
 * slot id, a transcript poller and a template-feedback list — three requests
 * keyed on something a candidate does not own. On the platform a station a
 * person sat *is* an attempt, and both halves hang off it, so the whole screen
 * is two capability components and a heading.
 *
 * Neither half asks who is looking: the same components render a candidate's
 * own record and the one an examiner reads while marking, and the API decides
 * which attempts a person may open.
 */
export function StationRecord({ attemptId }: { attemptId: string }) {
  const transcript = useAsync((signal) => readTranscript(attemptId, signal), [attemptId]);

  return (
    <div className="flex w-full min-w-0 flex-col gap-6">
      <header className="border-b border-b2b-border pb-4">
        <p className={b2bTokens.b2bEyebrow}>Station record</p>
        <h1 className={`mt-1 ${b2bTokens.b2bPageTitle}`}>Your consultation</h1>
      </header>

      <section className="space-y-2">
        <h2 className={b2bTokens.b2bEyebrow}>Feedback</h2>
        <AttemptFeedback attemptId={attemptId} showAll />
      </section>

      <section className="space-y-2">
        <h2 className={b2bTokens.b2bEyebrow}>Transcript</h2>
        <AsyncBoundary state={transcript}>
          {(data) => <TranscriptView transcript={data} />}
        </AsyncBoundary>
      </section>
    </div>
  );
}
