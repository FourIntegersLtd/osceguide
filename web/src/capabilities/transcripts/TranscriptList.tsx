"use client";

import Link from "next/link";
import { useCallback, useMemo } from "react";
import { HiOutlineArrowRight } from "react-icons/hi2";
import Table, {
  type FetchPageParams,
  type FetchPageResult,
} from "@/foundation/table/Table";
import { AsyncBoundary, cn } from "@/foundation/ui";
import { b2cTableCellText } from "@/foundation/ui/productTokens";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import {
  formatAttemptDate,
  kindLabel,
  listTranscribableAttempts,
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
 * Nothing here knows which arm it is mounted on: an institution's trainee gets
 * their own consultations from the same component and the same call.
 */
export function TranscriptList() {
  const state = useAsync((signal) => listTranscribableAttempts(signal), []);

  return (
    <div className="space-y-6 py-8 lg:px-4">
      <h1 className="text-left text-osce-title font-bold text-osce-ink-900">Transcripts</h1>

      <AsyncBoundary
        state={state}
        empty={{
          title: "No transcripts yet",
          description:
            "A transcript is saved each time you complete a consultation. Sit a station and it appears here.",
        }}
      >
        {(attempts) => <TranscriptTable attempts={attempts} />}
      </AsyncBoundary>
    </div>
  );
}

function TranscriptTable({ attempts }: { attempts: RecentAttempt[] }) {
  const { hrefFor } = useSurface();

  const numbered = useMemo(
    () => attempts.map((attempt, index) => ({ ...attempt, rowNumber: index + 1 })),
    [attempts],
  );

  const fetchPage = useCallback(
    async (params: FetchPageParams): Promise<FetchPageResult<TranscriptRow>> => {
      let filtered = numbered;
      if (params.search) {
        const q = params.search.toLowerCase();
        filtered = numbered.filter(
          (attempt) =>
            formatAttemptDate(attempt.created_at).toLowerCase().includes(q) ||
            attempt.exam_code.toLowerCase().includes(q) ||
            kindLabel(attempt.kind).toLowerCase().includes(q),
        );
      }
      const start = (params.page - 1) * params.perPage;
      const end = start + params.perPage;
      return {
        items: filtered.slice(start, end),
        totalCount: filtered.length,
      };
    },
    [numbered],
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
    <Table<TranscriptRow>
      fetchPage={fetchPage}
      columns={columns}
      idField="id"
      nameField="exam_code"
      searchPlaceholder="Search by date, exam or session type…"
    />
  );
}
