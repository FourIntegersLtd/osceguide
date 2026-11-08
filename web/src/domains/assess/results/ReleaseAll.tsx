"use client";

import { toggleInSet } from "@/domains/assess/support";
import { useCallback, useMemo, useState } from "react";
import { b2bTokens as t } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { releaseDecisions } from "@/domains/assess/results/api";
import type { CandidateReport } from "@/domains/assess/results/api";
import { RELEASE_HELPER, releaseResultsLabel } from "@/domains/assess/results/hireDecisions";
import { ReleaseButton } from "@/domains/assess/results/DecisionParts";
import { boardCard, boardRow, boardAlert } from "@/foundation/ui/boardKit";
import { boardCheck } from "@/domains/assess/results/resultsChrome";
import { sittingNext, type SittingStepsInput } from "@/domains/assess/sittingSteps";
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
  const hire = progress.words?.hiring === true && !progress.training;
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
    <>
      <div className={boardCard}>
        <div className={`${boardRow} justify-between border-t-0`}>
          <h2 className="text-base font-semibold leading-normal">Candidates to release</h2>
          <span className={t.assessMeta}>Untick a person to keep their result private for now. You can release it later.</span>
        </div>
        <fieldset className="m-0 min-w-0 border-0 p-0">
          <legend className="sr-only">Candidates to release</legend>
          {waiting.length > 1 ? (
            <label className={`${boardRow} ${boardCheck}`}>
              <input
                type="checkbox"
                className="mt-0.5 h-[18px] w-[18px]"
                checked={allPicked}
                disabled={busy}
                onChange={() =>
                  setHeld(allPicked ? new Set(waiting.map((candidate) => candidate.user_id)) : new Set())
                }
              />
              All {waiting.length}
            </label>
          ) : null}
          {waiting.map((candidate) => (
            <label key={candidate.user_id} className={`${boardRow} ${boardCheck}`}>
              <input
                type="checkbox"
                className="mt-0.5 h-[18px] w-[18px]"
                checked={picked.has(candidate.user_id)}
                disabled={busy}
                onChange={() => toggle(candidate.user_id)}
              />
              {candidate.name ?? candidate.email ?? "Candidate"}
            </label>
          ))}
        </fieldset>
      </div>
      {next.actionable && next.id === "release" ? (
        <div className="flex flex-wrap items-center gap-2.5">
          <ReleaseButton
            busy={busy}
            disabled={busy || chosen.length === 0}
            count={chosen.length}
            label={hire ? releaseResultsLabel(chosen.length) : `Release ${chosen.length} signed-off ${chosen.length === 1 ? "result" : "results"}`}
            onConfirm={() => void release()}
          />
          {hire ? <span className={t.assessMeta}>{RELEASE_HELPER}</span> : null}
        </div>
      ) : null}
      {released !== null ? (
        <div role="status" className={boardAlert(failures.length === 0 ? "ok" : "warn")}>
          {released} released{failures.length > 0 ? `, ${failures.length} refused.` : "."}
        </div>
      ) : null}
      {failures.length > 0 ? (
        <div role="alert" className={boardAlert("bad")}>
          <b className="block font-medium">Not released</b>
          <ul className="m-0 list-inside list-disc space-y-1 p-0">
            {failures.map((failure) => (
              <li key={failure}>{failure}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </>
  );
}
