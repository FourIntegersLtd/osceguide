"use client";

import {
  Badge,
  B2CGroupedRow,
  B2CGroupedRowLink,
  B2CGroupedSection,
  Spinner,
} from "@/foundation/ui";
import type { StationFeedbackState } from "@/domains/train/mocks/model";

/**
 * Each station in a finished session with where its feedback is (canvas
 * `train-complete`): a link once it is marked, otherwise why there is none
 * yet. A station that finished marking while the page was open says so.
 */
export function StationOutcomes({
  rows,
  readyIds,
  feedbackHref,
}: {
  rows: { entryId: string; label: string; feedback: StationFeedbackState }[];
  /** Stations seen marking on this visit that have since been marked. */
  readyIds: ReadonlySet<string>;
  feedbackHref: (entryId: string) => string;
}) {
  if (rows.length === 0) return null;
  return (
    <B2CGroupedSection eyebrow="Station outcomes">
      {rows.map((row) =>
        row.feedback === "review" ? (
          <B2CGroupedRowLink
            key={row.entryId}
            href={feedbackHref(row.entryId)}
            title={row.label}
            trailing={
              <span className="flex items-center gap-3">
                {readyIds.has(row.entryId) ? (
                  <Badge tone="success" dot>
                    Feedback ready
                  </Badge>
                ) : null}
                <span className="text-osce-meta font-medium text-osce-accent">View feedback</span>
              </span>
            }
          />
        ) : (
          <B2CGroupedRow
            key={row.entryId}
            title={row.label}
            trailing={
              row.feedback === "marking" ? (
                <span className="inline-flex items-center gap-2 text-osce-meta text-b2c-text-muted">
                  <Spinner size="xs" label="Marking" />
                  Marking
                </span>
              ) : (
                <span className="text-osce-meta text-b2c-text-muted">
                  {/* The old client could not tell a failed marking from none;
                      saying "Not attempted" would be false. */}
                  {row.feedback === "failed"
                    ? "Could not be marked"
                    : row.feedback === "unread"
                      ? "Could not check feedback"
                      : "Not attempted"}
                </span>
              )
            }
          />
        ),
      )}
    </B2CGroupedSection>
  );
}
