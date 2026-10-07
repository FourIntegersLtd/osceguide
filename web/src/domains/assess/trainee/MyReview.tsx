"use client";

import { useRouter } from "next/navigation";
import {
  Alert,
  AsyncBoundary,
  B2CGroupedRow,
  B2CGroupedSection,
  B2CHero,
  B2CPageHeader,
  Badge,
} from "@/foundation/ui";
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
  const router = useRouter();
  const state = useAsync((signal) => readMyReview(slotId, signal), [slotId]);

  return (
    <div className="flex w-full min-w-0 flex-col gap-6">
      <B2CPageHeader
        className="!mb-0"
        back={{ label: "Back", onClick: () => router.back() }}
        eyebrow="Your review"
        title="Station feedback"
      />

      {!state.loading && !state.error && state.data === null ? (
        <Alert tone="info" title="Not ready yet">
          This station&apos;s feedback appears once it is shared with you: in practice when your supervisor completes their review, in an exam when your result is released.
        </Alert>
      ) : null}
      <AsyncBoundary state={state}>
        {(review) => {
          const rating = review.summary.rating ?? null;
          const overall = review.summary.overall_rag;
          const outcome = passWord(review.summary.passed);
          const domains = summaryDomains(review.summary);
          return (
            <>
              <B2CHero
                eyebrow="Overall"
                title={ratingLabel(rating, overall)}
                aside={
                  outcome ? (
                    <Badge tone={review.summary.passed ? "success" : "danger"}>{outcome}</Badge>
                  ) : undefined
                }
              >
                {review.notes ? <span className="whitespace-pre-wrap">{review.notes}</span> : null}
              </B2CHero>

              {domains.length > 0 ? (
                <B2CGroupedSection eyebrow="By domain">
                  {domains.map((domain) => (
                    <B2CGroupedRow
                      key={domain.id}
                      title={domain.label}
                      trailing={
                        <Badge tone={ratingVariant(rating, domain.value)}>
                          {ratingLabel(rating, domain.value)}
                        </Badge>
                      }
                    />
                  ))}
                </B2CGroupedSection>
              ) : null}

              {review.completed_at ? (
                <p className="text-osce-caption text-b2b-mid">
                  Completed {new Date(review.completed_at).toLocaleString()}
                </p>
              ) : null}
            </>
          );
        }}
      </AsyncBoundary>
    </div>
  );
}

