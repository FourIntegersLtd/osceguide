"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { HiOutlineArrowRight } from "react-icons/hi2";
import Table from "@/foundation/table/Table";
import { AsyncBoundary, Button, SectionSearchField, cn } from "@/foundation/ui";
import { b2cTableCellText } from "@/foundation/ui/productTokens";
import { useCursorPages } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import {
  formatAttemptDate,
  kindLabel,
  listTranscribableAttempts,
  TRANSCRIPT_PAGE_LIMIT,
  type RecentAttempt,
} from "@/capabilities/transcripts/api";

type TranscriptRow = RecentAttempt & { rowNumber: number };

/**
 * Every consultation this person can read back.
 *
 * The retiring screen took a mock, a station and a user in its query string
 * and listed that one station's transcripts, so arriving at `/transcripts`
 * from the menu showed an empty state telling you to go and find a station
 * first. A transcript belongs to an attempt, and the attempt history is the
 * list — so this is it, whole, in one place.
 *
 * A page at a time, searched in SQL: this used to walk up to 25 pages of 100
 * before drawing anything, invisibly capped at 2,500 attempts.
 *
 * Nothing here knows which arm it is mounted on: an institution's trainee gets
 * their own consultations from the same component and the same call.
 */
export function TranscriptList() {
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");

  useEffect(() => {
    const timer = window.setTimeout(() => setQuery(search.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  const pages = useCursorPages(
    (cursor, signal) =>
      listTranscribableAttempts({ cursor, limit: TRANSCRIPT_PAGE_LIMIT, search: query }, signal),
    [query],
  );

  return (
    <div className="space-y-6 py-8 lg:px-4">
      <h1 className="text-left text-osce-title font-bold text-osce-ink-900">Transcripts</h1>

      <SectionSearchField
        value={search}
        onChange={setSearch}
        placeholder="Search by exam or session type…"
        ariaLabel="Search transcripts"
      />

      <AsyncBoundary
        state={pages.state}
        empty={{
          title: "No transcripts yet",
          description:
            "A transcript is saved each time you complete a consultation. Sit a station and it appears here.",
        }}
      >
        {(attempts) => (
          <TranscriptTable
            attempts={attempts}
            hasMore={pages.hasMore}
            loadingMore={pages.loadingMore}
            moreError={pages.moreError}
            onLoadMore={pages.loadMore}
          />
        )}
      </AsyncBoundary>
    </div>
  );
}

function TranscriptTable({
  attempts,
  hasMore,
  loadingMore,
  moreError,
  onLoadMore,
}: {
  attempts: RecentAttempt[];
  hasMore: boolean;
  loadingMore: boolean;
  moreError: Error | null;
  onLoadMore: () => void;
}) {
  const { hrefFor } = useSurface();

  const numbered = useMemo(
    () => attempts.map((attempt, index) => ({ ...attempt, rowNumber: index + 1 })),
    [attempts],
  );

  const columns = useMemo(
    () => [
      {
        header: "#",
        key: "rowNumber" as keyof TranscriptRow,
        priority: "detail" as const,
        render: (attempt: TranscriptRow) => (
          <span className="rounded-full bg-b2c-secondary px-3 py-1 text-osce-data text-osce-ink-900">
            {attempt.rowNumber}
          </span>
        ),
      },
      {
        header: "Date",
        key: "created_at" as keyof TranscriptRow,
        render: (attempt: TranscriptRow) => (
          <span className={b2cTableCellText}>{formatAttemptDate(attempt.created_at)}</span>
        ),
      },
      {
        header: "Session",
        key: "exam_code" as keyof TranscriptRow,
        priority: "primary" as const,
        render: (attempt: TranscriptRow) => (
          <span className={b2cTableCellText}>
            {attempt.exam_code.toUpperCase()} · {kindLabel(attempt.kind)}
          </span>
        ),
      },
      {
        header: "Action",
        key: "id" as keyof TranscriptRow,
        render: (attempt: TranscriptRow) => (
          <Link
            href={hrefFor(`/transcripts/${attempt.id}`)}
            className={cn("group flex cursor-pointer items-center space-x-2", b2cTableCellText)}
          >
            <span className="font-medium text-osce-accent">View details</span>
            <HiOutlineArrowRight
              className="h-4 w-4 text-osce-accent transition-transform group-hover:translate-x-1"
              aria-hidden
            />
          </Link>
        ),
      },
    ],
    [hrefFor],
  );

  return (
    <div className="space-y-4">
      <Table<TranscriptRow>
        data={numbered}
        columns={columns}
        idField="id"
        nameField="exam_code"
        showSearch={false}
        showPagination={false}
        totalItems={numbered.length}
        currentPage={1}
        itemsPerPage={Math.max(numbered.length, 1)}
        onPageChange={() => {}}
        onItemsPerPageChange={() => {}}
        onSearch={() => {}}
      />

      {moreError ? (
        <p className="text-osce-body text-osce-danger">
          Could not load more transcripts: {moreError.message}
        </p>
      ) : null}
      {hasMore ? (
        <div className="flex justify-center">
          <Button type="button" variant="secondary" size="sm" disabled={loadingMore} onClick={onLoadMore}>
            {loadingMore ? "Loading…" : "Load more transcripts"}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
