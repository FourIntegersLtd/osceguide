"use client";

import { useMemo, useState } from "react";
import Table from "@/foundation/table/Table";
import { AsyncBoundary, B2CPageHeader, Button, ButtonLink, SectionSearchField } from "@/foundation/ui";
import { b2cTableCellText } from "@/foundation/ui/productTokens";
import { useCursorPages, useSearchQuery } from "@/foundation/hooks";
import { formatLongDateTime } from "@/foundation/format";
import { useSurface } from "@/capabilities";
import {
  kindLabel,
  listTranscribableAttempts,
  TRANSCRIPT_PAGE_LIMIT,
  type RecentAttempt,
} from "@/capabilities/transcripts/api";

type TranscriptRow = RecentAttempt;

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
  const query = useSearchQuery(search);

  const pages = useCursorPages(
    (cursor, signal) =>
      listTranscribableAttempts({ cursor, limit: TRANSCRIPT_PAGE_LIMIT, search: query }, signal),
    [query],
  );

  return (
    <div className="mx-auto max-w-osce-page space-y-6">
      <B2CPageHeader
        title="Transcripts"
        subtitle="A transcript is saved each time you complete a consultation."
      />

      <SectionSearchField
        value={search}
        onChange={setSearch}
        placeholder="Search by exam or session type"
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


  const columns = useMemo(
    () => [
      {
        header: "Date",
        key: "created_at" as keyof TranscriptRow,
        render: (attempt: TranscriptRow) => (
          <span className={b2cTableCellText}>{formatLongDateTime(attempt.created_at)}</span>
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
        header: "",
        key: "id" as keyof TranscriptRow,
        render: (attempt: TranscriptRow) => (
          <ButtonLink href={hrefFor(`/transcripts/${attempt.id}`)} variant="secondary" size="sm">
            View details
          </ButtonLink>
        ),
      },
    ],
    [hrefFor],
  );

  return (
    <div className="space-y-4">
      <Table<TranscriptRow>
        data={attempts}
        columns={columns}
        idField="id"
        nameField="exam_code"
        showSearch={false}
        showPagination={false}
        totalItems={attempts.length}
        currentPage={1}
        itemsPerPage={Math.max(attempts.length, 1)}
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
