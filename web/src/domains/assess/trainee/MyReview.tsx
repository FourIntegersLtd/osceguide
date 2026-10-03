"use client";

import { AsyncBoundary, B2CPageHeader, Badge, b2bTokens } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { passWord, ratingLabel } from "@/capabilities/feedback/rubric";
import { ratingVariant, summaryDomains } from "@/domains/assess/results/reviewForm";
import { readMyReview } from "@/domains/assess/trainee/api";

/**
 * A candidate's own review of one station, once the GP lead has completed
 * one and not before. Mirrors `MyResult`'s release gate: the server decides
 * whether there is anything to show, this screen only renders what came back.
 *
 * Ratings are written in the rubric's own kind (`summary.rating`), so a
 * G / A / R station, a 0-4 station and a met / not met station all read right;
 * domains carry the rubric's own titles (`summary.domain_labels`).
 */
export function MyReview({ slotId }: { slotId: string }) {
  const state = useAsync((signal) => readMyReview(slotId, signal), [slotId]);

  return (
    <div className="flex w-full min-w-0 flex-col gap-6">
      <B2CPageHeader className="!mb-0" eyebrow="Your review" title="Station feedback" />

      <AsyncBoundary state={state}>
        {(review) => {
          const rating = review.summary.rating ?? null;
          const overall = review.summary.overall_rag;
          const outcome = passWord(review.summary.passed);
          const domains = summaryDomains(review.summary);
          return (
          <section className="space-y-5 rounded-panel border border-b2b-border bg-b2b-surface p-5 sm:p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className={b2bTokens.b2bEyebrow}>Overall</p>
                <p className="mt-1 text-osce-title font-semibold text-b2b-headline">
                  {ratingLabel(rating, overall)}
                </p>
              </div>
              {outcome ? <Badge tone={review.summary.passed ? "success" : "danger"}>{outcome}</Badge> : null}
            </div>

            {domains.length > 0 ? (
              <div>
                <h2 className={b2bTokens.b2bSectionTitle}>By domain</h2>
                <ul className="mt-2 divide-y divide-b2b-border rounded-panel border border-b2b-border">
                  {domains.map((domain) => (
                    <li
                      key={domain.id}
                      className="flex items-center justify-between gap-3 px-4 py-2.5"
                    >
                      <span className="text-osce-body text-b2b-graphite">{domain.label}</span>
                      <Badge tone={ratingVariant(rating, domain.value)}>{ratingLabel(rating, domain.value)}</Badge>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {review.notes ? (
              <div>
                <h2 className={b2bTokens.b2bSectionTitle}>What was said</h2>
                <p className="mt-2 whitespace-pre-wrap text-osce-body leading-relaxed text-b2b-graphite">
                  {review.notes}
                </p>
              </div>
            ) : null}

            {review.completed_at ? (
              <p className="text-osce-caption text-b2b-mid">
                Completed {new Date(review.completed_at).toLocaleString()}
              </p>
            ) : null}
          </section>
          );
        }}
      </AsyncBoundary>
    </div>
  );
}

