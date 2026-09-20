"use client";

import Link from "next/link";
import { useCallback, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { HiChevronUp } from "react-icons/hi2";
import Table, {
  type FetchPageParams,
  type FetchPageResult,
} from "@/foundation/table/Table";
import { Button, cn } from "@/foundation/ui";
import { b2cTableCellText } from "@/foundation/ui/productTokens";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { listMyAttempts } from "@/capabilities/attempt-runner";
import type { SetEntry, StationSet } from "@/domains/train/api";

export interface StationRow {
  entry: SetEntry;
  title: string;
}

type StationTableRow = StationRow & { position: number; id: string };

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

  const toggleRow = (entryId: string) =>
    setExpandedRows((prev) => ({ ...prev, [entryId]: !prev[entryId] }));

  const attemptHref = (entryId: string) => hrefFor(`/mocks/${set.id}/stations/${entryId}`);

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
    </>
  );

  const pool = useMemo(
    () => rows.map((row, index) => ({ ...row, position: index + 1, id: row.entry.id })),
    [rows],
  );

  const fetchPage = useCallback(
    async (params: FetchPageParams): Promise<FetchPageResult<StationTableRow>> => {
      let filtered = pool;
      if (params.search) {
        const q = params.search.toLowerCase();
        filtered = pool.filter((row) => row.title.toLowerCase().includes(q));
      }
      const start = (params.page - 1) * params.perPage;
      const end = start + params.perPage;
      return {
        items: filtered.slice(start, end),
        totalCount: filtered.length,
      };
    },
    [pool],
  );

  const columns = useMemo(
    () => [
      {
        header: "Station",
        key: "position" as keyof StationTableRow,
        priority: "detail" as const,
        render: (row: StationTableRow) => (
          <span className="rounded-md bg-b2c-secondary px-3 py-1 text-osce-data text-osce-ink-900">
            {row.position}
          </span>
        ),
      },
      {
        header: "Station name",
        key: "title" as keyof StationTableRow,
        priority: "primary" as const,
        render: (row: StationTableRow) => (
          <div className="flex items-center gap-2">
            <HiChevronUp
              className={cn(
                "h-5 w-5 shrink-0 transition-transform",
                expandedRows[row.entry.id] && "rotate-180",
              )}
              aria-hidden
            />
            <Link
              href={attemptHref(row.entry.id)}
              className={cn(b2cTableCellText, "text-osce-ink-900 hover:text-osce-accent")}
              onClick={(event) => event.stopPropagation()}
            >
              {row.title}
            </Link>
          </div>
        ),
      },
      {
        header: "Attempts",
        key: "entry" as keyof StationTableRow,
        render: (row: StationTableRow) => (
          <span className={cn("text-osce-data", attemptsClass(row.entry), b2cTableCellText)}>
            {attemptsLabel(row.entry)}
          </span>
        ),
      },
      {
        header: "Action",
        key: "entry" as keyof StationTableRow,
        priority: "secondary" as const,
        render: (row: StationTableRow) => (
          <div className="flex items-center gap-3" onClick={(event) => event.stopPropagation()}>
            {actions(row.entry, false)}
          </div>
        ),
      },
    ],
    [attemptHref, attemptLimit, expandedRows, set.locked],
  );

  return (
    <div>
      <Table<StationTableRow>
        fetchPage={fetchPage}
        columns={columns}
        idField="id"
        nameField="title"
        showSearch={false}
        showPagination={pool.length > 10}
        defaultItemsPerPage={25}
        isRowExpanded={(row) => Boolean(expandedRows[row.entry.id])}
        onRowActivate={(row) => toggleRow(row.entry.id)}
        renderExpandedRow={(row) => (
          <div className="flex w-full flex-col items-stretch gap-3 sm:flex-row sm:items-center sm:justify-end">
            <EntryHistory setId={set.id} entry={row.entry} />
          </div>
        )}
      />
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
