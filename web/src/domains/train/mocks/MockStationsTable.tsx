"use client";

import { Fragment, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { HiArrowRight, HiChevronUp } from "react-icons/hi2";
import { Alert, Button, cn, productTokens } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { listMyAttempts } from "@/capabilities/attempt-runner";
import { startSetDebrief } from "@/domains/train/api";
import type { SetEntry, StationSet } from "@/domains/train/api";

export interface StationRow {
  entry: SetEntry;
  title: string;
}

/**
 * The stations in a session, with where each one is up to.
 *
 * The expander is the old client's, and now so is what is behind it: the row
 * counts this entry's transcripts and markings and links to them. It said "No
 * transcripts yet" unconditionally for the whole port, because there was no
 * listing of a person's attempts to count; `GET /me/attempts` is that listing.
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
  const [busyEntryId, setBusyEntryId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const toggleRow = (entryId: string) =>
    setExpandedRows((prev) => ({ ...prev, [entryId]: !prev[entryId] }));

  const attemptHref = (entryId: string) => hrefFor(`/mocks/${set.id}/stations/${entryId}`);

  /** Talk the attempt through with the tutor, out loud. */
  const talkItThrough = async (entryId: string) => {
    setBusyEntryId(entryId);
    setError(null);
    try {
      const started = await startSetDebrief(set.id, entryId);
      router.push(hrefFor(`/debriefs/${started.attempt_id}`));
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusyEntryId(null);
    }
  };

  const attemptsLabel = (entry: SetEntry) =>
    entry.attempts >= attemptLimit ? "Completed" : `${entry.attempts}/${attemptLimit} attempts`;

  const attemptsClass = (entry: SetEntry) =>
    entry.attempts >= attemptLimit ? "text-osce-success-text" : "text-b2c-text-secondary";

  const actions = (entry: SetEntry, fullWidth: boolean) => (
    <>
      {entry.attempts !== 0 && (
        <Button
          type="button"
          variant="secondary"
          fullWidth={fullWidth}
          onClick={(event) => {
            event.preventDefault();
            event.stopPropagation();
            router.push(`${attemptHref(entry.id)}?action=review&tab=management`);
          }}
        >
          Review Last Attempt
        </Button>
      )}
      {!set.locked && entry.attempts < attemptLimit && (
        <Button
          type="button"
          fullWidth={fullWidth}
          onClick={(event) => {
            event.preventDefault();
            event.stopPropagation();
            router.push(attemptHref(entry.id));
          }}
        >
          Start New Attempt
        </Button>
      )}
      {entry.attempts !== 0 && (
        <Button
          type="button"
          variant="secondary"
          fullWidth={fullWidth}
          disabled={busyEntryId === entry.id}
          onClick={(event) => {
            event.preventDefault();
            event.stopPropagation();
            void talkItThrough(entry.id);
          }}
          className="gap-2"
        >
          {busyEntryId === entry.id ? "Starting…" : "Talk Through Last Attempt"}
          <HiArrowRight className="h-4 w-4" />
        </Button>
      )}
    </>
  );

  const expansion = (entry: SetEntry) => <EntryHistory setId={set.id} entry={entry} />;

  return (
    <div>
      {error ? (
        <Alert tone="danger" className="mb-3">
          {error}
        </Alert>
      ) : null}

      {/* Desktop Table View */}
      <div className="hidden overflow-x-auto rounded-lg border border-b2c-border lg:block">
        <table data-b2c-table="" className="min-w-full divide-y divide-b2c-border">
          <thead className={productTokens.b2cTableThead}>
            <tr>
              <th className={`min-w-[100px] px-6 py-3 text-left ${productTokens.b2cTableHeader}`}>
                Station
              </th>
              <th className={`min-w-[200px] px-6 py-3 text-left ${productTokens.b2cTableHeader}`}>
                Station Name
              </th>
              <th className={`min-w-[150px] px-6 py-3 text-left ${productTokens.b2cTableHeader}`}>
                Attempts
              </th>
              <th className={`min-w-[150px] px-6 py-3 text-left ${productTokens.b2cTableHeader}`}>
                Action
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-b2c-border bg-osce-surface">
            {rows.map(({ entry, title }, index) => (
              <Fragment key={entry.id}>
                <tr
                  className="cursor-pointer transition-colors hover:bg-b2c-surface-muted"
                  onClick={() => toggleRow(entry.id)}
                >
                  <td className={cn("whitespace-nowrap px-6 py-4", productTokens.b2cTableCell)}>
                    <span className="rounded-md bg-b2c-secondary px-3 py-1 text-osce-data text-osce-ink-900">
                      {index + 1}
                    </span>
                  </td>
                  <td className={cn("whitespace-nowrap px-6 py-4", productTokens.b2cTableCell)}>
                    <div className="flex items-center gap-2">
                      <HiChevronUp
                        className={cn(
                          "h-5 w-5 transition-transform",
                          expandedRows[entry.id] && "rotate-180",
                        )}
                      />
                      <Link
                        href={attemptHref(entry.id)}
                        className="text-osce-ink-900 hover:text-osce-accent"
                        onClick={(event) => event.stopPropagation()}
                      >
                        {title}
                      </Link>
                    </div>
                  </td>
                  <td className={cn("whitespace-nowrap px-6 py-4", productTokens.b2cTableCell)}>
                    <div className="flex items-center">
                      <span className={cn("text-osce-data", attemptsClass(entry))}>
                        {attemptsLabel(entry)}
                      </span>
                    </div>
                  </td>
                  <td className={cn("whitespace-nowrap px-6 py-4", productTokens.b2cTableCell)}>
                    <div className="flex items-center gap-3">{actions(entry, false)}</div>
                  </td>
                </tr>
                {expandedRows[entry.id] && (
                  <tr>
                    <td colSpan={4} className="bg-b2c-surface-muted px-6 py-4">
                      <div className="flex w-full flex-col items-stretch gap-3 sm:flex-row sm:items-center sm:justify-end">
                        {expansion(entry)}
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile Card View */}
      <div className="space-y-4 lg:hidden">
        {rows.map(({ entry, title }, index) => (
          <div
            key={entry.id}
            className="overflow-hidden rounded-none border border-b2c-border bg-osce-surface"
          >
            <div
              className="cursor-pointer p-5 transition-colors hover:bg-b2c-surface-muted"
              onClick={() => toggleRow(entry.id)}
            >
              <div className="mb-4 flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <span className="rounded-md bg-b2c-secondary px-3 py-1 text-osce-body font-medium text-osce-ink-900">
                    {index + 1}
                  </span>
                  <HiChevronUp
                    className={cn(
                      "h-5 w-5 text-b2c-text-muted transition-transform",
                      expandedRows[entry.id] && "rotate-180",
                    )}
                  />
                </div>
                <span className={cn("text-osce-body font-medium", attemptsClass(entry))}>
                  {attemptsLabel(entry)}
                </span>
              </div>

              <Link
                href={attemptHref(entry.id)}
                className="text-osce-body font-medium text-osce-ink-900 transition-colors hover:text-osce-accent"
                onClick={(event) => event.stopPropagation()}
              >
                {title}
              </Link>
            </div>

            <div className="space-y-3 px-5 pb-5">{actions(entry, true)}</div>

            {expandedRows[entry.id] && (
              <div className="space-y-3 border-t border-b2c-border bg-b2c-surface-muted px-5 pb-5 pt-3">
                <div className="flex items-center justify-center gap-2 rounded-md bg-b2c-secondary px-4 py-3 text-osce-body text-b2c-text-muted">
                  No transcripts yet
                </div>
                <div className="flex items-center justify-center gap-2 rounded-md bg-b2c-secondary px-4 py-3 text-osce-body text-b2c-text-muted">
                  No feedbacks yet
                </div>
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
 * Both counts were hard-coded empty states for the whole port — there was no
 * listing of a person's attempts to count. Each links back into the station
 * screen, which is where both are actually read.
 */
function EntryHistory({ setId, entry }: { setId: string; entry: SetEntry }) {
  const { hrefFor } = useSurface();
  const state = useAsync(
    (signal) => listMyAttempts({ setEntryId: entry.id, limit: 25 }, signal),
    [entry.id],
  );

  const stationHref = hrefFor(`/mocks/${setId}/stations/${entry.id}`);
  const attempts = state.data?.items ?? [];
  const marked = attempts.filter((item) => item.has_result).length;

  return (
    <div className="flex items-center gap-3">
      <Pill
        href={attempts.length > 0 ? `${stationHref}?action=review&tab=simulation` : null}
        label={
          attempts.length > 0 ? `All previous Transcripts (${attempts.length})` : "No transcripts yet"
        }
      />
      <Pill
        href={marked > 0 ? `${stationHref}?action=review&tab=feedback` : null}
        label={marked > 0 ? `All previous Feedbacks (${marked})` : "No feedbacks yet"}
      />
    </div>
  );
}

function Pill({ href, label }: { href: string | null; label: string }) {
  const className =
    "flex min-w-[200px] items-center justify-center gap-2 rounded-md bg-b2c-secondary px-5 py-2.5 text-osce-body";
  if (!href) {
    return <div className={cn(className, "text-b2c-text-muted")}>{label}</div>;
  }
  return (
    <Link href={href} className={cn(className, "text-osce-accent hover:text-osce-accent-hover")}>
      {label}
    </Link>
  );
}
