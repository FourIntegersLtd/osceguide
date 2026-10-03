"use client";

import { AsyncBoundary, Back, productTokens } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { TranscriptView } from "@/capabilities/feedback";
import { readTranscript } from "@/capabilities/transcripts/api";

/**
 * One consultation, read back.
 *
 * `id` is the attempt's, because a transcript has no id of its own on the
 * platform — it is one row per attempt, which is the shape the retiring
 * backend's separate `transcripts` collection was pretending not to be.
 *
 * The bubbles themselves are `TranscriptView` from the feedback capability:
 * the same component renders a candidate's own transcript and the one an
 * examiner reads while marking, so the two can never drift apart.
 */
export function TranscriptDetail({ id }: { id: string }) {
  const state = useAsync((signal) => readTranscript(id, signal), [id]);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="space-y-3">
        <Back />
        <h1 className={productTokens.b2cPageTitle}>Transcript details</h1>
      </div>
      <AsyncBoundary state={state}>
        {(transcript) => <TranscriptView transcript={transcript} />}
      </AsyncBoundary>
    </div>
  );
}
