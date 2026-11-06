"use client";

import { EmptyState } from "@/foundation/ui";
import { boardChip } from "@/foundation/ui/boardKit";
import { passWord, ratingLabel } from "@/capabilities/feedback/rubric";
import type { SlotReviews } from "@/domains/assess/results/api";
import { finishedReviewers, ratingVariant, reviewersAgreeLine, summaryDomains } from "@/domains/assess/results/reviewForm";

/**
 * What everybody who watched this station made of it.
 *
 * A slot has as many reviews as it had observers, and the summary is about the
 * set — so the backend answers them together rather than as a page. The worst
 * rating wins per domain, deliberately: when two reviewers disagree about a
 * candidate, the lower rating is the one that should prompt a conversation.
 *
 * Ratings are written in the rubric's own kind (`summary.rating`): a letter,
 * "3/4", or met / not met. Domains are named by the summary's own `domain_labels`.
 *
 * Drafts are counted and not shown. A half-written judgement of somebody is
 * not something to put in front of the next reviewer.
 */
const CHIP_TONE = { success: "ok", warning: "warn", danger: "live", neutral: "neutral" } as const;

export function SlotReviewers({
  reviews,
}: {
  /** Read by the screen that owns the slot, so this is not a second request. */
  reviews: SlotReviews;
}) {
  const data = reviews;
  const summary = data.summary;
  const rating = summary.rating ?? data.form?.rating ?? null;
  const outcome = passWord(summary.passed);
  const completed = summary.completed_reviews;
  const drafts = (data.items ?? []).filter((item) => item.status !== "completed").length;
  const byDomain = summaryDomains(summary);
  const reviewers = finishedReviewers(data.items, rating);
  const agreeLine = reviewersAgreeLine(data.reviewers_agree);

  if (completed === 0) {
    return (
      <EmptyState
        title="Nobody has finished a review of this station."
        description={drafts > 0 ? `${drafts} in progress.` : undefined}
      />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-assess-meta text-osce-ink-500">
          {completed} completed review{completed === 1 ? "" : "s"}
          {drafts > 0 ? ` · ${drafts} still in progress` : ""}
        </span>
        {summary.overall_rag !== null && summary.overall_rag !== undefined ? (
          <span className={boardChip(CHIP_TONE[ratingVariant(rating, summary.overall_rag)])}>
            Agreed: {ratingLabel(rating, summary.overall_rag)}
          </span>
        ) : null}
        {outcome ? <span className={boardChip(summary.passed ? "ok" : "live")}>{outcome}</span> : null}
      </div>

      {reviewers.length > 0 ? (
        <ul className="divide-y divide-osce-border-light">
          {reviewers.map((reviewer, index) => (
            <li key={`${index}-${reviewer.name}`} className="flex items-center justify-between gap-3 py-2.5">
              <span className="min-w-0 truncate text-assess-meta font-medium text-osce-ink-900">{reviewer.name}</span>
              <span className="text-assess-meta text-osce-ink-500">{reviewer.rating}</span>
            </li>
          ))}
        </ul>
      ) : null}
      {agreeLine ? <p className="text-assess-meta text-osce-ink-500">{agreeLine}</p> : null}

      {byDomain.length > 0 ? (
        <ul className="divide-y divide-osce-border-light">
          {byDomain.map((domain) => (
            <li key={domain.id} className="flex items-center justify-between gap-3 py-2.5">
              <span className="min-w-0 truncate text-assess-meta font-medium text-osce-ink-900">
                {domain.label}
              </span>
              <span className={boardChip(CHIP_TONE[ratingVariant(rating, domain.value)])}>{ratingLabel(rating, domain.value)}</span>
            </li>
          ))}
        </ul>
      ) : null}

      <p className="text-assess-meta text-osce-ink-500">
        Where reviewers disagreed, the lower rating is the one shown.
      </p>
    </div>
  );
}
