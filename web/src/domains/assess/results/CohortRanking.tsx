"use client";

import { Alert, Badge, Spinner, b2bTokens } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { hasCode } from "@/foundation/platform-client";
import { readCohort } from "@/domains/assess/results/api";
import { ReadoutExport } from "@/domains/assess/results/ReadoutExport";
import {
  PRIORITY_LABEL,
  candidateName,
  cohortSubtitle,
  formatCompletion,
  priorityTone,
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
 * to sit — so a training sitting answers 422 and this renders nothing.
 */
export function CohortRanking({ orgSlug, sittingId }: { orgSlug: string; sittingId: string }) {
  const state = useAsync(async (signal) => {
    try {
      return await readCohort(orgSlug, sittingId, signal);
    } catch (cause) {
      if (hasCode(cause, "not_an_exam_sitting")) return null;
      throw cause;
    }
  }, [orgSlug, sittingId]);

  if (state.loading) return <Spinner />;
  if (state.error) return <Alert tone="danger">{errorMessage(state.error)}</Alert>;

  const summary = state.data;
  if (!summary) return null;

  const candidates = summary.candidates ?? [];
  if (candidates.length === 0) return null;

  return (
    <section className="space-y-2">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className={b2bTokens.b2bEyebrow}>Review order</h2>
          <p className="text-osce-caption text-b2b-mid">
            {summary.cohort_size} candidate{summary.cohort_size === 1 ? "" : "s"}, ranked on what is
            unfinished before what is poor.
          </p>
        </div>
        {/* Same place the retiring cohort report put it: beside the ranking it
            is drawn from. The read-out is the whole document — this table, the
            recommendations and the method — rather than what is on screen. */}
        <ReadoutExport orgSlug={orgSlug} sittingId={sittingId} />
      </div>

      <ol className={b2bTokens.b2bGroupedShell}>
        {candidates.map((candidate) => (
          <li key={candidate.trainee.user_id} className={b2bTokens.b2bGroupedRow}>
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-b2b-cream text-osce-caption font-bold text-b2b-mid">
              {candidate.rank}
            </span>
            <div className="min-w-0 flex-1">
              <p className={b2bTokens.b2bGroupedRowTitle}>{candidateName(candidate.trainee)}</p>
              <p className={b2bTokens.b2bGroupedRowSubtitle}>
                {cohortSubtitle(candidate)} · {formatCompletion(candidate.completion_rate)} complete
              </p>
            </div>
            <Badge variant={priorityTone(candidate.review_priority)}>
              {PRIORITY_LABEL[candidate.review_priority] ?? candidate.review_priority}
            </Badge>
          </li>
        ))}
      </ol>
    </section>
  );
}
