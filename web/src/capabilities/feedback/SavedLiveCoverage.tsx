"use client";

import { useAsync } from "@/foundation/hooks";
import { AsyncBoundary } from "@/foundation/ui";
import { readCoverage } from "@/capabilities/attempt-runner/coverage/api";
import { FeedbackLiveCoverage } from "./FeedbackLiveCoverage";

export function SavedLiveCoverage({ attemptId }: { attemptId: string }) {
  const state = useAsync((signal) => readCoverage(attemptId, signal), [attemptId]);
  return <AsyncBoundary state={state}>{(coverage) => <FeedbackLiveCoverage coverage={
    [...(coverage.items ?? [])].sort((a, b) => a.seq - b.seq).map((item) => ({
      ...item, id: item.competency_id, covered: item.state === "covered", quote: item.quote ?? null,
    }))
  } />}</AsyncBoundary>;
}
