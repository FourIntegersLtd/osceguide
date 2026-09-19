"use client";

import { Badge, EmptyState, b2bTokens } from "@/foundation/ui";
import { RAG_LABEL, type Rag } from "@/capabilities/feedback";
import type { SlotReviews } from "@/domains/assess/results/api";

/**
 * What everybody who watched this station made of it.
 *
 * A slot has as many reviews as it had observers, and the summary is about the
 * set — so the backend answers them together rather than as a page. The worst
 * rating wins per domain, deliberately: when two reviewers disagree about a
 * candidate, the lower rating is the one that should prompt a conversation.
 *
 * Drafts are counted and not shown. A half-written judgement of somebody is
 * not something to put in front of the next reviewer.
 */
export function SlotReviewers({
  reviews,
  labelFor,
}: {
  /** Read by the screen that owns the slot, so this is not a second request. */
  reviews: SlotReviews;
  /** Domain keys to the words the rest of the screen uses for them. */
  labelFor?: (key: string) => string;
}) {
  const data = reviews;
  const summary = data.summary;
  const completed = summary.completed_reviews;
  const drafts = (data.items ?? []).filter((item) => item.status !== "submitted").length;
  const byDomain = Object.entries(summary.by_domain ?? {});

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
        <span className="text-osce-caption text-b2b-mid">
          {completed} completed review{completed === 1 ? "" : "s"}
          {drafts > 0 ? ` · ${drafts} still in progress` : ""}
        </span>
        {summary.overall_rag ? (
          <Badge variant={ragTone(summary.overall_rag)}>
            Agreed: {RAG_LABEL[summary.overall_rag as Rag] ?? summary.overall_rag}
          </Badge>
        ) : null}
      </div>

      {byDomain.length > 0 ? (
        <ul className="divide-y divide-b2b-border rounded-lg border border-b2b-border">
          {byDomain.map(([key, rag]) => (
            <li key={key} className="flex items-center justify-between gap-3 px-3 py-2.5">
              <span className="min-w-0 truncate text-osce-caption font-medium text-b2b-headline">
                {labelFor ? labelFor(key) : key}
              </span>
              <Badge variant={ragTone(rag)}>{RAG_LABEL[rag as Rag] ?? rag}</Badge>
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

function ragTone(rag: string): "success" | "warning" | "danger" | "neutral" {
  if (rag === "G") return "success";
  if (rag === "A") return "warning";
  if (rag === "R") return "danger";
  return "neutral";
}
