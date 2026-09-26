"use client";

import { Fragment, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { HiArrowRight, HiChevronUp } from "react-icons/hi2";
import { Button, cn, productTokens } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { listMyAttempts } from "@/capabilities/attempt-runner";
import type { SetEntry, StationSet } from "@/domains/train/api";
import { attemptsWithTranscript } from "@/domains/train/mocks/model";

const { b2cGhostButton, b2cTableCell, b2cTableHeader, b2cTableThead } = productTokens;

export interface StationRow {
  entry: SetEntry;
  title: string;
}

/**
 * The stations in a session, with where each one is up to.
 *
 * A table on a wide screen and a card per station on a phone, as the retiring
 * client drew it. A row opens to count this entry's transcripts and markings
 * and link to them; those counts were hard-coded empty for most of the port,
 * because there was no listing of a person's attempts until `GET /me/attempts`.
 */
export function MockStationsTable({
  set,
  rows,
  attemptLimit,
}: {
  set: StationSet;
  rows: StationRow[];
  attemptLimit: number;
}) {
  const router = useRouter();
  const { hrefFor } = useSurface();
  const [expandedRows, setExpandedRows] = useState<Record<string, boolean>>({});

  const toggleRow = (entryId: string) =>
    setExpandedRows((previous) => ({ ...previous, [entryId]: !previous[entryId] }));

  const stationHref = (entryId: string) => hrefFor(`/mocks/${set.id}/stations/${entryId}`);

  const isCompleted = (entry: SetEntry) => entry.attempts >= attemptLimit;
  const attemptsLabel = (entry: SetEntry) =>
    isCompleted(entry) ? "Completed" : `${entry.attempts}/${attemptLimit} attempts`;
  const attemptsTone = (entry: SetEntry) =>
    isCompleted(entry) ? "text-osce-success-text" : "text-b2c-text-secondary";

  const startButton = (entry: SetEntry, fullWidth: boolean) =>
    !set.locked && !isCompleted(entry) ? (
      <Button
        type="button"
        fullWidth={fullWidth}
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          router.push(`${stationHref(entry.id)}?action=attempt`);
        }}
      >
        Start New Attempt
      </Button>
    ) : null;

  const reviewButton = (entry: SetEntry, fullWidth: boolean) =>
    entry.attempts !== 0 ? (
      <Button
        type="button"
        variant="secondary"
        fullWidth={fullWidth}
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          router.push(`${stationHref(entry.id)}?action=review&tab=management`);
        }}
        className="gap-2"
      >
        Review Last Attempt
        <HiArrowRight className="h-4 w-4" />
      </Button>
    ) : null;

  return (
    <div>
      {/* Desktop table */}
      <div className="hidden overflow-x-auto rounded-lg border border-b2c-border lg:block">
        <table data-b2c-table="" className="min-w-full divide-y divide-b2c-border">
          <thead className={b2cTableThead}>
            <tr>
              <th className={`min-w-[100px] px-6 py-3 text-left ${b2cTableHeader}`}>Station</th>
              <th className={`min-w-[200px] px-6 py-3 text-left ${b2cTableHeader}`}>
                Station Name
              </th>
              <th className={`min-w-[150px] px-6 py-3 text-left ${b2cTableHeader}`}>Attempts</th>
              <th className={`min-w-[150px] px-6 py-3 text-left ${b2cTableHeader}`}>Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-b2c-border bg-osce-surface">
            {rows.map((row, index) => (
              <Fragment key={row.entry.id}>
                <tr
                  className="cursor-pointer transition-colors hover:bg-b2c-surface-muted"
                  onClick={() => toggleRow(row.entry.id)}
                >
                  <td className={cn("whitespace-nowrap px-6 py-4", b2cTableCell)}>
                    <span className="rounded-md bg-b2c-secondary px-3 py-1 text-osce-data text-osce-ink-900">
                      {index + 1}
                    </span>
                  </td>
                  <td className={cn("whitespace-nowrap px-6 py-4", b2cTableCell)}>
                    <div className="flex items-center gap-2">
                      <HiChevronUp
                        className={cn(
                          "h-5 w-5 transition-transform",
                          expandedRows[row.entry.id] && "rotate-180",
                        )}
                      />
                      <Link
                        href={stationHref(row.entry.id)}
                        className="text-osce-ink-900 hover:text-osce-accent"
                        onClick={(event) => event.stopPropagation()}
                      >
                        {row.title}
                      </Link>
                    </div>
                  </td>
                  <td className={cn("whitespace-nowrap px-6 py-4", b2cTableCell)}>
                    <div className="flex items-center">
                      <span className={cn("text-osce-data", attemptsTone(row.entry))}>
                        {attemptsLabel(row.entry)}
                      </span>
                    </div>
                  </td>
                  <td className={cn("whitespace-nowrap px-6 py-4", b2cTableCell)}>
                    <div className="flex items-center gap-3">
                      {startButton(row.entry, false)}
                      {reviewButton(row.entry, false)}
                    </div>
                  </td>
                </tr>
                {expandedRows[row.entry.id] && (
                  <tr>
                    <td colSpan={4} className="bg-b2c-surface-muted px-6 py-4">
                      <div className="flex w-full flex-col items-stretch gap-3 sm:flex-row sm:items-center sm:justify-end">
                        <div className="flex items-center gap-3">
                          <EntryHistory stationHref={stationHref(row.entry.id)} entry={row.entry} />
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile cards */}
      <div className="space-y-4 lg:hidden">
        {rows.map((row, index) => (
          <div
            key={row.entry.id}
            className="overflow-hidden rounded-none border border-b2c-border bg-osce-surface"
          >
            <div
              className="cursor-pointer p-5 transition-colors hover:bg-b2c-surface-muted"
              onClick={() => toggleRow(row.entry.id)}
            >
              <div className="mb-4 flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <span className="rounded-md bg-b2c-secondary px-3 py-1 text-osce-body font-medium text-osce-ink-900">
                    {index + 1}
                  </span>
                  <HiChevronUp
                    className={cn(
                      "h-5 w-5 text-b2c-text-muted transition-transform",
                      expandedRows[row.entry.id] && "rotate-180",
                    )}
                  />
                </div>
                <span className={cn("text-osce-body font-medium", attemptsTone(row.entry))}>
                  {attemptsLabel(row.entry)}
                </span>
              </div>

              <Link
                href={stationHref(row.entry.id)}
                className="text-osce-body font-medium text-osce-ink-900 transition-colors hover:text-osce-accent"
                onClick={(event) => event.stopPropagation()}
              >
                {row.title}
              </Link>
            </div>

            <div className="space-y-3 px-5 pb-5">
              {startButton(row.entry, true)}
              {reviewButton(row.entry, true)}
            </div>

            {expandedRows[row.entry.id] && (
              <div className="space-y-3 border-t border-b2c-border bg-b2c-surface-muted px-5 pb-5 pt-3">
                <EntryHistory stationHref={stationHref(row.entry.id)} entry={row.entry} compact />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * What this station has produced: its transcripts and its markings.
 *
 * Each links into the station screen, which is where both are read: the old
 * client's `/transcripts` and `/feedbacks` lists filtered by station have no
 * equivalent here, and the station's own review tabs are the same content.
 */
function EntryHistory({
  stationHref,
  entry,
  compact = false,
}: {
  stationHref: string;
  entry: SetEntry;
  /** The phone layout: full-width rows rather than two fixed-width pills. */
  compact?: boolean;
}) {
  const state = useAsync(
    (signal) => listMyAttempts({ setEntryId: entry.id, limit: 25 }, signal),
    [entry.id],
  );
  const attempts = state.data?.items ?? [];
  // Only an attempt that finished its consultation left a transcript; one
  // still `created` or `running` never sat the station.
  const transcripts = attemptsWithTranscript(attempts).length;
  const feedbacks = attempts.filter((item) => item.has_result).length;

  return (
    <>
      <HistoryLink
        href={`${stationHref}?action=review&tab=simulation`}
        count={transcripts}
        label="All previous Transcripts"
        emptyLabel="No transcripts yet"
        compact={compact}
      />
      <HistoryLink
        href={`${stationHref}?action=review&tab=feedback`}
        count={feedbacks}
        label="All previous Feedbacks"
        emptyLabel="No feedbacks yet"
        compact={compact}
      />
    </>
  );
}

function HistoryLink({
  href,
  count,
  label,
  emptyLabel,
  compact,
}: {
  href: string;
  count: number;
  label: string;
  emptyLabel: string;
  compact: boolean;
}) {
  if (count === 0) {
    return (
      <div
        className={cn(
          "flex items-center justify-center gap-2 rounded-md bg-b2c-secondary text-osce-body text-b2c-text-muted",
          compact ? "px-4 py-3" : "min-w-[200px] px-5 py-2.5",
        )}
      >
        {emptyLabel}
      </div>
    );
  }
  return (
    <Link
      href={href}
      className={cn(
        b2cGhostButton,
        compact ? "w-full justify-between gap-2 group" : "min-w-[200px] justify-center gap-2 group",
      )}
    >
      <span>
        {label} ({count})
      </span>
      <HiArrowRight className="h-4 w-4 transition-transform duration-200 group-hover:translate-x-1" />
    </Link>
  );
}
