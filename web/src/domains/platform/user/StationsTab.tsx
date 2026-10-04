"use client";

import Link from "next/link";
import { useState } from "react";
import {
  AsyncBoundary,
  Badge,
  Button,
  ConfirmModal,
  Panel,
  Row,
  RowList,
} from "@/foundation/ui";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import { hasCode } from "@/foundation/platform-client";
import { useSurface } from "@/capabilities";
import {
  deleteStationProgress,
  listUserStations,
  resetStationAttempts,
  type StationProgress,
} from "@/domains/platform/support/api";
import {
  attemptStatusLabel,
  attemptStatusTone,
  formatMoment,
} from "@/domains/platform/support";
import { InlineAction } from "@/domains/platform/user/InlineAction";

/**
 * The retiring console's "Station progress" card, with its two buttons.
 *
 * Reset zeroes the counters the per-station limit is enforced on and keeps
 * every record; Delete erases the attempts, transcripts and marking and takes
 * the station out of their practice sets. The row shows both counts — the
 * attempts that exist and the counter — because after a reset they differ,
 * and that difference is the whole explanation of what reset did.
 */
export function StationsTab({ userId }: { userId: string }) {
  const state = useAsync(
    (signal) => listUserStations(userId, signal),
    [userId],
  );
  return (
    <Panel
      title="Station progress"
      description="Every station this person has taken. Their attempt limit is checked against this count."
      padding="none"
    >
      <AsyncBoundary
        state={state}
        empty={{
          title: "No stations yet",
          description: "This person has not sat anything.",
          bare: true,
        }}
      >
        {(rows) => (
          <RowList flush>
            {rows.map((row) => (
              <StationRow
                key={row.station_id}
                userId={userId}
                row={row}
                onChanged={state.reload}
              />
            ))}
          </RowList>
        )}
      </AsyncBoundary>
    </Panel>
  );
}

function StationRow({
  userId,
  row,
  onChanged,
}: {
  userId: string;
  row: StationProgress;
  onChanged: () => void;
}) {
  const { hrefFor } = useSurface();
  const toast = useToast();
  const [confirmReset, setConfirmReset] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = async () => {
    setBusy(true);
    setError(null);
    try {
      const change = await resetStationAttempts(userId, row.station_id);
      toast.success(
        `Attempts reset for ${row.title}`,
        change.entries_reset === 0
          ? "This station is not in any of their practice sets, so there was no count to reset."
          : `${change.entries_reset} counter${change.entries_reset === 1 ? "" : "s"} set to 0. The attempts are kept.`,
      );
      setConfirmReset(false);
      onChanged();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  const remove = async (reason: string) => {
    try {
      const change = await deleteStationProgress(
        userId,
        row.station_id,
        reason,
      );
      toast.success(
        `${row.title} deleted from their history`,
        `${change.attempts_deleted} attempt${change.attempts_deleted === 1 ? "" : "s"} and ${
          change.entries_removed
        } set entr${change.entries_removed === 1 ? "y" : "ies"} removed.`,
      );
      onChanged();
    } catch (cause) {
      if (hasCode(cause, "attempt_in_progress")) {
        throw new Error(
          "One attempt at this station is still running. Wait for it to end, or fail it from Attempts, then try again.",
        );
      }
      throw cause;
    }
  };

  return (
    <Row className="flex-col items-stretch gap-3">
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="truncate text-osce-data font-medium text-ink">
            {row.title}{" "}
            <span className="text-osce-meta font-normal text-ink-subtle">
              · {row.exam_code.toUpperCase()}
            </span>
          </p>
          <p className="truncate text-osce-meta text-ink-subtle">
            {row.attempts} attempt{row.attempts === 1 ? "" : "s"} ·{" "}
            {row.evaluated} marked · counter {row.entry_attempts}
            {row.last_attempt_at
              ? ` · last ${formatMoment(row.last_attempt_at)}`
              : ""}
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {row.last_status ? (
            <Badge tone={attemptStatusTone(row.last_status)}>
              {attemptStatusLabel(row.last_status)}
            </Badge>
          ) : null}
          {row.last_attempt_id ? (
            <Link
              href={hrefFor(
                `/attempts/${encodeURIComponent(row.last_attempt_id)}`,
              )}
            >
              <Button variant="ghost" size="sm">
                Newest attempt
              </Button>
            </Link>
          ) : null}
          <Button
            variant="secondary"
            size="sm"
            disabled={busy}
            onClick={() => setConfirmReset(true)}
          >
            Reset attempts
          </Button>
          <InlineAction
            label="Delete progress"
            tone="danger"
            description="Removes every attempt, transcript and marking at this station and takes it out of their practice sets. This cannot be undone."
            onConfirm={remove}
          />
        </div>
      </div>
      <ConfirmModal
        isOpen={confirmReset}
        onCancel={() => {
          setConfirmReset(false);
          setError(null);
        }}
        onConfirm={() => reset()}
        isLoading={busy}
        error={error}
        title="Reset attempts?"
        confirmText="Yes, reset"
        message={`Reset attempts for "${row.title}" to 0? Their attempts and marking are kept; they may sit it again.`}
      />
    </Row>
  );
}
