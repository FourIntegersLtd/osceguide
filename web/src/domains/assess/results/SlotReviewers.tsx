"use client";

import { Badge, EmptyState, b2bTokens } from "@/foundation/ui";
import { passWord, ratingLabel } from "@/capabilities/feedback/rubric";
import type { SlotReviews } from "@/domains/assess/results/api";
import { ratingVariant, summaryDomains } from "@/domains/assess/results/reviewForm";

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

  if (completed === 0) {
    return (
      <EmptyState
        title="Nobody has finished a review of this station."
        description={drafts > 0 ? `${drafts} in progress.` : undefined}
      />
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-osce-meta text-b2b-mid">
          {completed} completed review{completed === 1 ? "" : "s"}
          {drafts > 0 ? ` · ${drafts} still in progress` : ""}
        </span>
        {summary.overall_rag !== null && summary.overall_rag !== undefined ? (
          <Badge variant={ratingVariant(rating, summary.overall_rag)}>
            Agreed: {ratingLabel(rating, summary.overall_rag)}
          </Badge>
        ) : null}
        {outcome ? <Badge variant={summary.passed ? "success" : "danger"}>{outcome}</Badge> : null}
      </div>

      {byDomain.length > 0 ? (
        <ul className="divide-y divide-b2b-border">
          {byDomain.map((domain) => (
            <li key={domain.id} className="flex items-center justify-between gap-3 py-2.5">
              <span className="min-w-0 truncate text-osce-meta font-medium text-b2b-headline">
                {domain.label}
              </span>
              <Badge variant={ratingVariant(rating, domain.value)} dot>{ratingLabel(rating, domain.value)}</Badge>
            </li>
          ))}
        </ul>
      ) : null}

      <p className={b2bTokens.b2bGroupedRowSubtitle}>
        Where reviewers disagreed, the lower rating is the one shown.
      </p>
    </div>
  );
}
