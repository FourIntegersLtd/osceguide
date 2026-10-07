"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useMemo } from "react";
import { HiArrowRight } from "react-icons/hi";
import { HiOutlineFaceFrown } from "react-icons/hi2";
import { AsyncBoundary, B2CEmptyState, ButtonLink } from "@/foundation/ui";
import Table, { type Column } from "@/foundation/table/Table";
import { useCursorPages } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { feedbackRows } from "@/capabilities/station-runner/feedbackRows";
import { listMyAttempts, type AttemptHistoryItem } from "@/capabilities/attempt-runner";

type FeedbackRow = ReturnType<typeof feedbackRows<AttemptHistoryItem>>[number];

export function FeedbackHistory({ stationVersionId, entryId, stationName }: {
  stationVersionId: string | null;
  entryId: string | null;
  stationName: string;
}) {
  const { hrefFor } = useSurface();
  const pathname = usePathname();
  // A server page at a time: every attempt at one station used to be walked
  // to the last cursor before a row was drawn.
  const pages = useCursorPages<AttemptHistoryItem>(
    (cursor, signal) =>
      stationVersionId || entryId
        ? listMyAttempts({ stationVersionId, setEntryId: entryId, limit: 100, cursor }, signal)
        : Promise.resolve({ items: [], next_cursor: null }),
    [stationVersionId, entryId],
  );

  const columns = useMemo<Column<FeedbackRow>[]>(
    () => [
      {
        header: "#",
        key: (item) => (
          <span className="rounded-full bg-b2c-secondary px-3 py-1 text-osce-data text-osce-ink-900">{item.position}</span>
        ),
        priority: "detail",
      },
      {
        header: "Date",
        key: (item) =>
          new Date(item.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" }),
        priority: "primary",
      },
      {
        header: "Action",
        key: (item) => (
          <Link href={hrefFor(`/attempts/${item.id}`)} className="group flex items-center space-x-2 text-osce-accent">
            <span className="font-medium">View Details</span>
            <HiArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
          </Link>
        ),
      },
    ],
    [hrefFor],
  );

  return <AsyncBoundary state={pages.state}>{(attempts) => {
    const rows = feedbackRows(attempts);
    // Nothing marked on the pages read so far is only "no feedback" once the server has no more.
    return rows.length === 0 && !pages.hasMore ? (
      <div className="rounded-lg bg-b2c-surface-muted p-10 text-center">
        <B2CEmptyState icon={HiOutlineFaceFrown} title="No Feedback History Found"
          description="You haven't received any feedback for this station yet." />
        <ButtonLink href={pathname + "?action=attempt"} className="mt-4">Attempt this station</ButtonLink>
      </div>
    ) : (
      <div className="space-y-6">
        <h1 className="text-left text-osce-body font-semibold text-osce-ink-900">Feedbacks for {stationName}</h1>
        <Table<FeedbackRow> rows={rows} more={pages} columns={columns} idField="id" minWidthClassName="min-w-full" />
      </div>
    );
  }}</AsyncBoundary>;
}
