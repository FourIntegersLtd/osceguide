"use client";

import { Alert, B2CGroupedRow, B2CGroupedSection, Badge, Spinner } from "@/foundation/ui";
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
    <B2CGroupedSection eyebrow="Review order" action={<ReadoutExport orgSlug={orgSlug} sittingId={sittingId} />}>
      <p className="px-4 pt-3 text-osce-meta text-b2b-mid">
        {summary.cohort_size} candidate{summary.cohort_size === 1 ? "" : "s"}, with unfinished reviews first, then the weakest results.
      </p>
      {candidates.map((candidate) => (
        <B2CGroupedRow
          key={candidate.trainee.user_id}
          title={`${candidate.rank}. ${candidateName(candidate.trainee)}`}
          meta={`${cohortSubtitle(candidate)} · ${formatCompletion(candidate.completion_rate)} complete`}
          trailing={
            <Badge variant={priorityTone(candidate.review_priority)} dot>
              {PRIORITY_LABEL[candidate.review_priority] ?? candidate.review_priority}
            </Badge>
          }
        />
      ))}
    </B2CGroupedSection>
  );
}
