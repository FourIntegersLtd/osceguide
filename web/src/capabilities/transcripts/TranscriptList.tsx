"use client";

import { useMemo, useState } from "react";
import Table, { type TableMore } from "@/foundation/table/Table";
import { AsyncBoundary, B2CPageHeader, ButtonLink, SectionSearchField } from "@/foundation/ui";
import { b2cTableCellText } from "@/foundation/ui/productTokens";
import { useCursorPages, useSearchQuery } from "@/foundation/hooks";
import { formatLongDateTime } from "@/foundation/format";
import { useSurface } from "@/capabilities";
import {
  listTranscribableAttempts,
  TRANSCRIPT_PAGE_LIMIT,
  type RecentAttempt,
} from "@/capabilities/transcripts/api";
import { attemptKindLabel } from "@/capabilities/transcripts/kindLabel";

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
          <TranscriptTable attempts={attempts} more={pages} />
        )}
      </AsyncBoundary>
    </div>
  );
}

function TranscriptTable({ attempts, more }: { attempts: RecentAttempt[]; more: TableMore }) {
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
            {attempt.exam_code.toUpperCase()} · {attemptKindLabel(attempt.kind)}
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
    <Table<TranscriptRow> rows={attempts} more={more} columns={columns} idField="id" />
  );
}
