"use client";

import { AsyncBoundary, Badge, b2bTokens } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { readMyReview } from "@/domains/assess/trainee/api";

/**
 * A candidate's own review of one station, once the GP lead has completed
 * one and not before. Mirrors `MyResult`'s release gate: the server decides
 * whether there is anything to show, this screen only renders what came back.
 */
export function MyReview({ slotId }: { slotId: string }) {
  const state = useAsync((signal) => readMyReview(slotId, signal), [slotId]);

  return (
    <div className="flex w-full min-w-0 flex-col gap-6">
      <header className="border-b border-b2b-border pb-4">
        <p className={b2bTokens.b2bEyebrow}>Your review</p>
        <h1 className={`mt-1 ${b2bTokens.b2bPageTitle}`}>Station feedback</h1>
      </header>

      <AsyncBoundary state={state}>
        {(review) => (
          <section className="space-y-5 rounded-lg border border-b2b-border bg-b2b-surface p-4 sm:p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className={b2bTokens.b2bEyebrow}>Overall</p>
                <p className="mt-1 text-osce-title font-semibold text-b2b-headline">
                  {ragLabel(review.summary.overall_rag)}
                </p>
              </div>
              {review.summary.overall_rag ? (
                <Badge tone={ragTone(review.summary.overall_rag)}>
                  {ragLabel(review.summary.overall_rag)}
                </Badge>
              ) : null}
            </div>

            {Object.keys(review.summary.by_domain).length > 0 ? (
              <div>
                <h2 className={b2bTokens.b2bSectionTitle}>By domain</h2>
                <ul className="mt-2 divide-y divide-b2b-border rounded-lg border border-b2b-border">
                  {Object.entries(review.summary.by_domain).map(([domainName, rating]) => (
                    <li
                      key={domainName}
                      className="flex items-center justify-between gap-3 px-4 py-2.5"
                    >
                      <span className="text-osce-body text-b2b-graphite">{domainName}</span>
                      <Badge tone={ragTone(rating)}>{ragLabel(rating)}</Badge>
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
        )}
      </AsyncBoundary>
    </div>
  );
}

function ragLabel(rag: string | null | undefined): string {
  if (!rag) return "Not rated";
  const labels: Record<string, string> = { red: "Needs work", amber: "Borderline", green: "Good" };
  return labels[rag.toLowerCase()] ?? rag;
}

function ragTone(rag: string | null | undefined): "success" | "danger" | "warning" | "neutral" {
  const value = rag?.toLowerCase();
  if (value === "green") return "success";
  if (value === "red") return "danger";
  if (value === "amber") return "warning";
  return "neutral";
}
