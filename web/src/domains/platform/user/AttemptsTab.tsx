"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
  AsyncBoundary,
  Badge,
  PlatformFilterBar,
  PlatformFilterSelect,
} from "@/foundation/ui";
import Table, { type Column } from "@/foundation/table/Table";
import { useCursorPages } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { attemptKindLabel } from "@/capabilities/transcripts/kindLabel";
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

  const columns = useMemo<Column<PlatformAttempt>[]>(
    () => [
      {
        header: "Attempt",
        key: "kind",
        priority: "primary",
        render: (attempt) => {
          const diagnosis = diagnoseAttempt(attempt);
          return (
            <Link
              href={hrefFor(`/attempts/${encodeURIComponent(attempt.id)}`)}
              className="block min-w-0"
            >
              <p className="truncate font-medium text-ink hover:underline">
                {attemptKindLabel(attempt.kind)} · {formatMoment(attempt.created_at)}
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
          );
        },
      },
      {
        header: "Status",
        key: "status",
        render: (attempt) => (
          <div className="flex flex-wrap items-center gap-2">
            {diagnoseAttempt(attempt) ? <Badge tone="danger" dot>Needs attention</Badge> : null}
            <Badge tone={attemptStatusTone(attempt.status)} dot>
              {attemptStatusLabel(attempt.status)}
            </Badge>
          </div>
        ),
      },
    ],
    [hrefFor],
  );

  return (
    <div className="flex flex-col gap-4">
      <PlatformFilterBar>
        <PlatformFilterSelect
          aria-label="Attempt status"
          value={status}
          onChange={setStatus}
        >
          <option value="">Every status</option>
          {ATTEMPT_STATUSES.map((value) => (
            <option key={value} value={value}>
              {attemptStatusLabel(value)}
            </option>
          ))}
        </PlatformFilterSelect>
      </PlatformFilterBar>
      <AsyncBoundary state={pages.state}>
        {(items) => (
          <Table<PlatformAttempt>
            rows={items}
            more={pages}
            themeType="b2b"
            idField="id"
            title="Attempts"
            description="Newest first. Each row says what, if anything, is wrong with it."
            columns={columns}
            empty={{
              title: "No attempts",
              description: status
                ? "None with that status."
                : "This person has not sat anything yet.",
            }}
          />
        )}
      </AsyncBoundary>
    </div>
  );
}
