"use client";

import { boardCard, boardRow, boardChip, type BoardChipTone } from "@/foundation/ui/boardKit";
import { Alert, Spinner, b2bTokens as t } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { readCohort } from "@/domains/assess/results/api";
import { ReadoutExport } from "@/domains/assess/results/ReadoutExport";
import {
  PRIORITY_LABEL,
  candidateName,
  cohortSubtitle,
  formatCompletion,
} from "@/domains/assess/results/support";

/**
 * Who a GP lead should look at first.
 *
 * Ranked by the backend, and completion ranks before score on purpose: a
 * candidate who sat three of five stations has a problem nobody has looked at,
 * while one who scored badly has at least been assessed. The retiring client
 * called this the cohort report and had a "refresh ranking" button because it
 * was cached; this is computed per request.
 *
 * Exam sittings only. A training circuit is people practising, and ranking
 * them against each other would turn practice into an assessment nobody agreed
 * to sit — so the server refuses a training sitting (422) and the results
 * screen mounts this for exam sittings only.
 */
export function CohortRanking({ orgSlug, sittingId }: { orgSlug: string; sittingId: string }) {
  const state = useAsync((signal) => readCohort(orgSlug, sittingId, signal), [orgSlug, sittingId]);

  if (state.loading) return <Spinner />;
  if (state.error) return <Alert tone="danger">{errorMessage(state.error)}</Alert>;

  const summary = state.data;
  if (!summary) return null;

  const candidates = summary.candidates ?? [];
  if (candidates.length === 0) return null;

  return (
    <div className={boardCard}>
      <div className={`${boardRow} justify-between border-t-0`}>
        <div>
          <div className={t.assessEyebrow}>Review order</div>
          <div className={t.assessMeta}>
            {summary.cohort_size} candidate{summary.cohort_size === 1 ? "" : "s"}, with unfinished reviews first, then the weakest results.
          </div>
        </div>
        <ReadoutExport orgSlug={orgSlug} sittingId={sittingId} />
      </div>
      {candidates.map((candidate) => (
        <div key={candidate.trainee.user_id} className={boardRow}>
          <span className="flex-1">
            {`${candidate.rank}. ${candidateName(candidate.trainee)}`}
            <div className={t.assessMeta}>
              {`${cohortSubtitle(candidate)} · ${formatCompletion(candidate.completion_rate)} complete`}
            </div>
          </span>
          {candidate.review_priority ? (
            <span className={boardChip(PRIORITY_CHIP[candidate.review_priority] ?? "neutral")}>
              {PRIORITY_LABEL[candidate.review_priority] ?? candidate.review_priority}
            </span>
          ) : null}
        </div>
      ))}
    </div>
  );
}

const PRIORITY_CHIP: Record<string, BoardChipTone> = { urgent: "live", high: "warn" };
