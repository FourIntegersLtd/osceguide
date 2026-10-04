"use client";

import { useState } from "react";
import Link from "next/link";
import { HiArrowRight, HiChevronDown } from "react-icons/hi2";
import { Badge, ButtonLink, Card, cn, productTokens } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { listMyAttempts } from "@/capabilities/attempt-runner";
import type { SetEntry, StationSet } from "@/domains/train/api";
import { attemptsWithTranscript } from "@/domains/train/mocks/model";

const { b2cIconButton } = productTokens;

export interface StationRow {
  entry: SetEntry;
  title: string;
}

/**
 * The stations in a session, with where each one is up to (canvas
 * `train-session`, attempted state).
 *
 * One list for every width: a row per station with its number, title,
 * attempts and next action, which wraps rather than switching to a second
 * layout on a phone. A row opens to count this entry's transcripts and
 * markings and link to them; those counts were hard-coded empty for most of
 * the port, because there was no listing of a person's attempts until
 * `GET /me/attempts`.
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
  const { hrefFor } = useSurface();
  const [expandedRows, setExpandedRows] = useState<Record<string, boolean>>({});

  const toggleRow = (entryId: string) =>
    setExpandedRows((previous) => ({ ...previous, [entryId]: !previous[entryId] }));

  const stationHref = (entryId: string) => hrefFor(`/mocks/${set.id}/stations/${entryId}`);

  return (
    <Card title="Stations" description={`${set.attempted_entries} of ${set.total_entries} attempted`}>
      <ul className="-mx-5 divide-y divide-osce-border-light border-t border-osce-border-light">
        {rows.map((row, index) => {
          const { entry } = row;
          const completed = entry.attempts >= attemptLimit;
          const canAttempt = !set.locked && !completed;
          const expanded = Boolean(expandedRows[entry.id]);
          const attemptHref = `${stationHref(entry.id)}?action=attempt`;
          const reviewHref = `${stationHref(entry.id)}?action=review&tab=management`;
          return (
            <li key={entry.id}>
              <div className="flex min-h-[54px] flex-wrap items-center gap-x-4 gap-y-2 px-5 py-3">
                <span className="inline-flex h-[22px] min-w-[28px] items-center justify-center rounded-[6px] bg-b2c-surface-muted px-1.5 font-mono text-osce-meta tabular-nums text-osce-ink-900">
                  {index + 1}
                </span>
                <div className="min-w-0 flex-1 basis-40">
                  <Link
                    href={stationHref(entry.id)}
                    className="block truncate text-osce-body font-medium text-osce-ink-900 hover:text-osce-accent"
                  >
                    {row.title}
                  </Link>
                </div>
                <div className="w-[120px] shrink-0">
                  {completed ? (
                    <Badge tone="success" dot>
                      Completed
                    </Badge>
                  ) : entry.attempts > 0 ? (
                    <span className="text-osce-meta tabular-nums text-b2c-text-muted">
                      {entry.attempts}/{attemptLimit} attempts
                    </span>
                  ) : (
                    <span className="text-osce-meta text-b2c-text-muted">Not attempted</span>
                  )}
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {completed || (set.locked && entry.attempts > 0) ? (
                    <ButtonLink href={reviewHref} variant="secondary" size="sm">
                      Review last attempt
                    </ButtonLink>
                  ) : canAttempt && entry.attempts > 0 ? (
                    <>
                      <ButtonLink href={attemptHref} variant="primary" size="sm">
                        Start new attempt
                      </ButtonLink>
                      <ButtonLink href={reviewHref} variant="secondary" size="sm">
                        Review
                      </ButtonLink>
                    </>
                  ) : canAttempt ? (
                    <ButtonLink href={attemptHref} variant="secondary" size="sm">
                      Start
                    </ButtonLink>
                  ) : null}
                  <button
                    type="button"
                    aria-expanded={expanded}
                    aria-label={`${expanded ? "Hide" : "Show"} history for ${row.title}`}
                    onClick={() => toggleRow(entry.id)}
                    className={b2cIconButton}
                  >
                    <HiChevronDown
                      aria-hidden
                      className={cn("h-4 w-4 transition-transform", expanded && "rotate-180")}
                    />
                  </button>
                </div>
              </div>
              {expanded ? (
                <div className="flex flex-col gap-2 bg-b2c-surface-muted px-5 py-3 sm:flex-row sm:justify-end">
                  <EntryHistory stationHref={stationHref(entry.id)} entry={entry} />
                </div>
              ) : null}
            </li>
          );
        })}
      </ul>
    </Card>
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
}: {
  stationHref: string;
  entry: SetEntry;
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
        label="Transcripts"
        emptyLabel="No transcripts yet"
      />
      <HistoryLink
        href={`${stationHref}?action=review&tab=feedback`}
        count={feedbacks}
        label="Feedback"
        emptyLabel="No feedback yet"
      />
    </>
  );
}

function HistoryLink({
  href,
  count,
  label,
  emptyLabel,
}: {
  href: string;
  count: number;
  label: string;
  emptyLabel: string;
}) {
  if (count === 0) {
    return <span className="px-2 py-1.5 text-osce-meta text-b2c-text-muted">{emptyLabel}</span>;
  }
  return (
    <Link
      href={href}
      className="group inline-flex items-center gap-1.5 rounded-control px-2 py-1.5 text-osce-meta font-medium text-osce-accent hover:bg-osce-surface"
    >
      {label} ({count})
      <HiArrowRight
        aria-hidden
        className="h-3.5 w-3.5 transition-transform duration-200 group-hover:translate-x-0.5"
      />
    </Link>
  );
}
