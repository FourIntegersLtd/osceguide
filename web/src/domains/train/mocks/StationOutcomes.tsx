"use client";

import { useRouter } from "next/navigation";
import { HiArrowRight } from "react-icons/hi";
import type { StationFeedbackState } from "@/domains/train/mocks/model";

const reviewLinkClass =
  "inline-flex items-center gap-1 font-semibold text-osce-accent hover:underline";

/**
 * Each station in a finished session with where its feedback is: a link once
 * it is marked, otherwise why there is none yet.
 */
export function StationOutcomes({
  rows,
  feedbackHref,
}: {
  rows: { entryId: string; label: string; feedback: StationFeedbackState }[];
  feedbackHref: (entryId: string) => string;
}) {
  const router = useRouter();
  return rows.length > 0 ? (
    <ul aria-label="Station outcomes" className="space-y-2 border-t border-b2c-border pt-4">
      {rows.map((row) => (
        <li
          key={row.entryId}
          className="flex flex-wrap items-center justify-between gap-2 text-osce-body text-b2c-text-secondary"
        >
          <span className="min-w-0 truncate">{row.label}</span>
          {row.feedback === "review" ? (
            <button
              type="button"
              onClick={() => router.push(feedbackHref(row.entryId))}
              className={reviewLinkClass}
            >
              View feedback
              <HiArrowRight className="h-4 w-4" aria-hidden />
            </button>
          ) : row.feedback === "marking" ? (
            <span className="text-osce-meta text-b2c-text-muted">Marking…</span>
          ) : row.feedback === "failed" ? (
            // The old client could not tell a failed marking
            // from none; saying "Not attempted" would be false.
            <span className="text-osce-meta text-b2c-text-muted">Couldn&apos;t be marked</span>
          ) : (
            <span className="text-osce-meta text-b2c-text-muted">Not attempted</span>
          )}
        </li>
      ))}
    </ul>
  ) : null;
}
