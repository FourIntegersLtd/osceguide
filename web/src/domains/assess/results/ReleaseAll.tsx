"use client";

import { toggleInSet } from "@/domains/assess/support";
import { useCallback, useMemo, useState } from "react";
import { Alert, Panel, StepGuide } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { releaseDecisions } from "@/domains/assess/results/api";
import type { CandidateReport } from "@/domains/assess/results/api";
import { ReleaseButton } from "@/domains/assess/results/DecisionParts";
import { sittingNext, sittingSteps, type SittingStepsInput } from "@/domains/assess/sittingSteps";
import {
  UNLINKED_REASON,
  releaseFailureLine,
  releaseRefusal,
  splitByAccount,
} from "@/domains/assess/results/support";

/**
 * Releasing signed-off decisions, several at once.
 *
 * Offers exactly what is signed off and not yet out, because that is the only
 * set the backend will accept anyway, each ticked by name so a lead can hold
 * one back (the retiring screen released a selection behind a
 * `window.confirm`). One request releases the lot; the backend runs each
 * through the single release, so each keeps its server-side evidence check and its own
 * `candidate_result_released` email. A candidate whose marking moved since
 * sign-off is skipped by the backend and named here with the reason.
 */
export function ReleaseAll({
  orgSlug,
  sittingId,
  waiting,
  onChanged,
  progress,
}: {
  orgSlug: string;
  sittingId: string;
  waiting: CandidateReport[];
  onChanged: () => void;
  progress: SittingStepsInput;
}) {
  const next = sittingNext(progress);
  const [busy, setBusy] = useState(false);
  const [failures, setFailures] = useState<string[]>([]);
  const [released, setReleased] = useState<number | null>(null);
  // Who is held back, not who is ticked: a release shrinks `waiting` and the
  // selection follows, so the result alert below survives it (no remount).
  const [held, setHeld] = useState<Set<string>>(new Set());
  const picked = useMemo(() => new Set(waiting.filter((c) => !held.has(c.user_id)).map((c) => c.user_id)), [waiting, held]);
  const chosen = useMemo(() => waiting.filter((candidate) => picked.has(candidate.user_id)), [waiting, picked]);
  const allPicked = chosen.length === waiting.length;

  const toggle = (id: string) => setHeld((current) => toggleInSet(current, id));

  const release = useCallback(async () => {
    setBusy(true);
    setFailures([]);
    setReleased(null);
    const { traineeIds, unlinked } = splitByAccount(chosen);
    const byTrainee = new Map(chosen.map((candidate) => [candidate.trainee_id, candidate]));
    try {
      const result = await releaseDecisions(
        orgSlug,
        sittingId,
        traineeIds.map((traineeId) => ({ traineeId })),
      );
      setReleased((result.released ?? []).length);
      setFailures([
        ...unlinked.map((candidate) => releaseFailureLine(candidate, UNLINKED_REASON)),
        ...(result.skipped ?? []).map((skip) =>
          releaseFailureLine(byTrainee.get(skip.trainee_id), releaseRefusal(skip.code)),
        ),
      ]);
    } catch (cause) {
      setFailures([errorMessage(cause instanceof Error ? cause : new Error(String(cause)))]);
    } finally {
      setBusy(false);
      onChanged();
    }
  }, [orgSlug, sittingId, chosen, onChanged]);

  return (
    <div className="space-y-3">
      <StepGuide steps={sittingSteps(progress)} line={next.line}>
        {next.actionable && next.id === "release" ? (
          <ReleaseButton
            busy={busy}
            disabled={busy || chosen.length === 0}
            count={chosen.length}
            label={`Release ${chosen.length} signed-off ${chosen.length === 1 ? "result" : "results"}`}
            onConfirm={() => void release()}
          />
        ) : null}
      </StepGuide>

      <Panel title="Candidates to release" description="Untick anyone to hold their result back." padding="sm">
      <fieldset className="space-y-2">
        <legend className="sr-only">Candidates to release</legend>
        {waiting.length > 1 ? (
          <label className="flex items-center gap-2 text-osce-meta font-medium text-b2b-headline">
            <input
              type="checkbox"
              checked={allPicked}
              disabled={busy}
              onChange={() =>
                setHeld(allPicked ? new Set(waiting.map((candidate) => candidate.user_id)) : new Set())
              }
            />
            All {waiting.length}
          </label>
        ) : null}
        <ul className="grid grid-cols-1 gap-1 sm:grid-cols-2">
          {waiting.map((candidate) => (
            <li key={candidate.user_id}>
              <label className="flex items-center gap-2 text-osce-body text-b2b-headline">
                <input
                  type="checkbox"
                  checked={picked.has(candidate.user_id)}
                  disabled={busy}
                  onChange={() => toggle(candidate.user_id)}
                />
                {candidate.name ?? candidate.email ?? "Candidate"}
              </label>
            </li>
          ))}
        </ul>
      </fieldset>
      </Panel>

      {released !== null ? (
        <Alert tone={failures.length === 0 ? "success" : "warning"}>
          {released} released{failures.length > 0 ? `, ${failures.length} refused.` : "."}
        </Alert>
      ) : null}
      {failures.length > 0 ? (
        <Alert tone="danger" title="Not released">
          <ul className="list-inside list-disc space-y-1">
            {failures.map((failure) => (
              <li key={failure}>{failure}</li>
            ))}
          </ul>
        </Alert>
      ) : null}
    </div>
  );
}
