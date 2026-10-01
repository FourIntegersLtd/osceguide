"use client";

import Link from "next/link";
import { useState } from "react";
import {
  AsyncBoundary,
  Badge,
  LoadMore,
  Panel,
  Row,
  RowList,
  Select,
} from "@/foundation/ui";
import { useCursorPages } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { kindLabel } from "@/capabilities/transcripts/api";
import {
  listUserAttempts,
  type PlatformAttempt,
} from "@/domains/platform/support/api";
import {
  ATTEMPT_STATUSES,
  attemptStatusLabel,
  attemptStatusTone,
  diagnoseAttempt,
  formatMoment,
} from "@/domains/platform/support";

const ATTEMPTS_PAGE_LIMIT = 25;

/**
 * One person's attempts, each saying whether anything is wrong with it.
 *
 * "I did the station and got no feedback" is the commonest ticket, and the
 * row answers it before anybody opens the attempt: `diagnoseAttempt` turns
 * the delivery state, the results and the queue into one sentence.
 */
export function AttemptsTab({ userId }: { userId: string }) {
  const { hrefFor } = useSurface();
  const [status, setStatus] = useState("");
  const pages = useCursorPages(
    (cursor, signal) =>
      listUserAttempts(
        userId,
        {
          status: status || null,
          cursor: cursor ?? undefined,
          limit: ATTEMPTS_PAGE_LIMIT,
        },
        signal,
      ),
    [userId, status],
  );

  return (
    <Panel
      title="Attempts"
      description="Newest first. Each row says what, if anything, is wrong with it."
      actions={
        <Select
          selectSize="sm"
          aria-label="Attempt status"
          className="w-44"
          value={status}
          onChange={(event) => setStatus(event.target.value)}
        >
          <option value="">Every status</option>
          {ATTEMPT_STATUSES.map((value) => (
            <option key={value} value={value}>
              {attemptStatusLabel(value)}
            </option>
          ))}
        </Select>
      }
      padding="none"
    >
      <AsyncBoundary
        state={pages.state}
        isEmpty={(items) => items.length === 0}
        empty={{
          title: "No attempts",
          description: status
            ? "None with that status."
            : "This person has not sat anything yet.",
          bare: true,
        }}
      >
        {(items) => (
          <>
            <RowList flush>
              {items.map((attempt) => (
                <AttemptRow
                  key={attempt.id}
                  attempt={attempt}
                  href={hrefFor(`/attempts/${encodeURIComponent(attempt.id)}`)}
                />
              ))}
            </RowList>
            <LoadMore
              hasMore={pages.hasMore}
              busy={pages.loadingMore}
              onLoad={pages.loadMore}
              error={pages.moreError}
            />
          </>
        )}
      </AsyncBoundary>
    </Panel>
  );
}

function AttemptRow({
  attempt,
  href,
}: {
  attempt: PlatformAttempt;
  href: string;
}) {
  const diagnosis = diagnoseAttempt(attempt);
  return (
    <Row className="flex-col items-stretch sm:flex-row sm:items-center">
      <Link href={href} className="min-w-0 flex-1">
        <p className="truncate text-osce-data font-medium text-ink">
          {kindLabel(attempt.kind)} · {formatMoment(attempt.created_at)}
        </p>
        <p className="truncate text-osce-meta text-ink-subtle">
          {diagnosis
            ? diagnosis.problem
            : attempt.result_policy_versions.length > 0
              ? `Marked under ${attempt.result_policy_versions.join(", ")}`
              : attempt.scoring_job
                ? `Marking ${attempt.scoring_job.status}`
                : attempt.failed_reason
                  ? `Failed: ${attempt.failed_reason}`
                  : "-"}
        </p>
      </Link>
      <div className="flex shrink-0 items-center gap-2">
        {diagnosis ? <Badge tone="danger">Needs attention</Badge> : null}
        <Badge tone={attemptStatusTone(attempt.status)}>
          {attemptStatusLabel(attempt.status)}
        </Badge>
      </div>
    </Row>
  );
}
