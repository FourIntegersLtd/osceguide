"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { format } from "date-fns";
import { HiChevronRight, HiOutlineChatBubbleLeftRight } from "react-icons/hi2";
import { AsyncBoundary, Alert, Button, cardScrollBody, productTokens } from "@/foundation/ui";
import { useCursorPages } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { debriefDate, listDebriefs } from "@/capabilities/debrief/api";
import { waitForDebrief } from "@/capabilities/debrief/waitForDebrief";

const { b2cCard, b2cGroupedRow, b2cGroupedRowSubtitle, b2cGroupedRowTitle } = productTokens;

/** A page at a time. The backend's page cap on `GET /me/debriefs` is 100. */
const DEBRIEF_HISTORY_PAGE_LIMIT = 25;

/**
 * The debriefs someone has had.
 *
 * `stationVersionId`/`entryId` scope to every source consultation for a
 * station or a set entry, `attemptId` to one consultation, and neither shows
 * the learner's complete history — all three filters run in SQL on
 * `GET /me/debriefs` rather than being reconstructed here from a walk of
 * `listMyAttempts`.
 *
 * `awaitingAttemptId` is a debrief that has just ended: its summary is still
 * being written, so the list says so and reloads once it is there.
 */
export function DebriefHistory({ attemptId, stationVersionId, entryId, awaitingAttemptId }: {
  attemptId?: string;
  stationVersionId?: string | null;
  entryId?: string | null;
  awaitingAttemptId?: string | null;
} = {}) {
  const { hrefFor } = useSurface();
  const [settled, setSettled] = useState<{ attemptId: string; status: "arrived" | "failed" } | null>(null);
  const wait = !awaitingAttemptId ? null : settled?.attemptId === awaitingAttemptId ? settled.status : "waiting";
  useEffect(() => {
    if (!awaitingAttemptId) return;
    const controller = new AbortController();
    void waitForDebrief(
      async (signal) =>
        (
          await listDebriefs(
            { attemptId: attemptId ?? null, stationVersionId: stationVersionId ?? null, setEntryId: entryId ?? null, limit: 5 },
            signal,
          )
        ).items.map((item) => item.attempt_id),
      awaitingAttemptId,
      { signal: controller.signal },
    )
      .then(() => {
        // Found or timed out, the list is read again and the notice goes.
        if (!controller.signal.aborted) setSettled({ attemptId: awaitingAttemptId, status: "arrived" });
      })
      .catch(() => {
        if (!controller.signal.aborted) setSettled({ attemptId: awaitingAttemptId, status: "failed" });
      });
    return () => controller.abort();
  }, [awaitingAttemptId, attemptId, stationVersionId, entryId]);
  const pages = useCursorPages(
    (cursor, signal) =>
      listDebriefs(
        {
          attemptId: attemptId ?? null,
          stationVersionId: stationVersionId ?? null,
          setEntryId: entryId ?? null,
          cursor,
          limit: DEBRIEF_HISTORY_PAGE_LIMIT,
        },
        signal,
      ),
    [attemptId, stationVersionId, entryId, wait === "arrived"],
  );
  const state = pages.state;

  return (
    <>
      {wait === "waiting" ? (
        <Alert tone="info" className="mb-4">
          Your debrief has ended. Athena is writing its summary, and it will appear here in a minute.
        </Alert>
      ) : null}
      {wait === "failed" ? (
        <Alert tone="warning" className="mb-4">
          We could not check whether your debrief summary is ready. Reload this page in a minute to look again.
        </Alert>
      ) : null}
      <AsyncBoundary
        state={state}
        empty={{
          title: "No debriefs yet",
          description:
            "Start a debrief from a station you have already sat to talk your consultation through with Athena.",
        }}
      >
        {(debriefs) => (
          <>
            <div className={`${b2cCard} ${cardScrollBody}`}>
              {debriefs.map((debrief) => {
                const created = debriefDate(debrief.created_at);
                return (
                  <Link
                    href={hrefFor(`/debriefs/${debrief.id}`)}
                    key={debrief.id}
                    className={b2cGroupedRow}
                  >
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-control bg-b2c-surface-muted text-osce-ink-900">
                      <HiOutlineChatBubbleLeftRight className="h-4 w-4" aria-hidden />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className={b2cGroupedRowTitle}>Debrief session</p>
                      <p className={b2cGroupedRowSubtitle}>
                        {created ? format(created, "PPP p") : ""}
                      </p>
                    </div>
                    <HiChevronRight className="h-4 w-4 shrink-0 text-b2c-text-muted" aria-hidden />
                  </Link>
                );
              })}
            </div>
            {pages.moreError ? (
              <Alert tone="danger">Could not load more: {pages.moreError.message}</Alert>
            ) : null}
            {pages.hasMore ? (
              <div className="mt-4 flex justify-center">
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={pages.loadingMore}
                  onClick={pages.loadMore}
                >
                  {pages.loadingMore ? "Loading…" : "Load more"}
                </Button>
              </div>
            ) : null}
          </>
        )}
      </AsyncBoundary>
    </>
  );
}
