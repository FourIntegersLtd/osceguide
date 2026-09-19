"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { AsyncBoundary, Badge, Button, Card } from "@/foundation/ui";
import { useAsync, useToast } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { kindLabel } from "@/capabilities/transcripts/api";
import { listUserAttempts, type PlatformAttempt } from "@/domains/platform/support/api";
import { LoadMore, Row, RowList } from "@/domains/platform/chrome";
import {
  ATTEMPT_STATUSES,
  attemptStatusLabel,
  attemptStatusTone,
  diagnoseAttempt,
  formatMoment,
} from "@/domains/platform/support";

/**
 * One person's attempts, each saying whether anything is wrong with it.
 *
 * "I did the station and got no feedback" is the commonest ticket, and the
 * row answers it before anybody opens the attempt: `diagnoseAttempt` turns
 * the delivery state, the results and the queue into one sentence.
 */
export function AttemptsTab({ userId }: { userId: string }) {
  const { hrefFor } = useSurface();
  const toast = useToast();
  const [status, setStatus] = useState<string>("");
  const state = useAsync((signal) => listUserAttempts(userId, { status: status || null }, signal), [userId, status]);
  const [extra, setExtra] = useState<PlatformAttempt[]>([]);
  const [cursor, setCursor] = useState<string | null | undefined>(undefined);
  const [busy, setBusy] = useState(false);

  const loadMore = useCallback(async () => {
    const next = cursor === undefined ? state.data?.next_cursor : cursor;
    if (!next) return;
    setBusy(true);
    try {
      const page = await listUserAttempts(userId, { status: status || null, cursor: next });
      setExtra((rows) => [...rows, ...page.items]);
      setCursor(page.next_cursor ?? null);
    } catch {
      toast.error("Could not load more attempts");
    } finally {
      setBusy(false);
    }
  }, [cursor, state.data, userId, status, toast]);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <Button variant={status ? "secondary" : "primary"} size="sm" onClick={() => setStatus("")}>
          All
        </Button>
        {ATTEMPT_STATUSES.map((value) => (
          <Button
            key={value}
            variant={status === value ? "primary" : "secondary"}
            size="sm"
            onClick={() => {
              setStatus(value);
              setExtra([]);
              setCursor(undefined);
            }}
          >
            {attemptStatusLabel(value)}
          </Button>
        ))}
      </div>
      <AsyncBoundary
        state={state}
        isEmpty={(page) => page.items.length === 0}
        empty={{ title: "No attempts", description: "This person has not sat anything yet." }}
      >
        {(page) => (
          <>
            <RowList>
              {[...page.items, ...extra].map((attempt) => (
                <AttemptRow
                  key={attempt.id}
                  attempt={attempt}
                  href={hrefFor(`/attempts/${encodeURIComponent(attempt.id)}`)}
                />
              ))}
            </RowList>
            <LoadMore
              cursor={cursor === undefined ? page.next_cursor : cursor}
              busy={busy}
              onLoad={() => void loadMore()}
            />
          </>
        )}
      </AsyncBoundary>
    </div>
  );
}

function AttemptRow({ attempt, href }: { attempt: PlatformAttempt; href: string }) {
  const diagnosis = diagnoseAttempt(attempt);
  return (
    <Row className="flex-col items-stretch sm:flex-row sm:items-center">
      <Link href={href} className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-ink">
          {kindLabel(attempt.kind)} · {formatMoment(attempt.created_at)}
        </p>
        <p className="truncate text-xs text-ink-subtle">
          {diagnosis
            ? diagnosis.problem
            : attempt.result_policy_versions.length > 0
              ? `Marked under ${attempt.result_policy_versions.join(", ")}`
              : attempt.scoring_job
                ? `Marking ${attempt.scoring_job.status}`
                : attempt.failed_reason
                  ? `Failed: ${attempt.failed_reason}`
                  : "—"}
        </p>
      </Link>
      <div className="flex shrink-0 items-center gap-2">
        {diagnosis ? <Badge tone="danger">Needs attention</Badge> : null}
        <Badge tone={attemptStatusTone(attempt.status)}>{attemptStatusLabel(attempt.status)}</Badge>
      </div>
    </Row>
  );
}

export function AttemptsEmpty() {
  return (
    <Card padding="md">
      <p className="text-sm text-ink-muted">No attempts.</p>
    </Card>
  );
}
