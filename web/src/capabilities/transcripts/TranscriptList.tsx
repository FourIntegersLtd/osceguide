"use client";

import Link from "next/link";
import { HiOutlineArrowRight } from "react-icons/hi2";
import { AsyncBoundary, cn, productTokens } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import {
  formatAttemptDate,
  kindLabel,
  listTranscribableAttempts,
} from "@/capabilities/transcripts/api";

const { b2cTableCell, b2cTableHeader, b2cTableThead } = productTokens;

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
  const { hrefFor } = useSurface();
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
        {(attempts) => (
          <div className="overflow-x-auto rounded-lg border">
            <table data-b2c-table="" className="min-w-full divide-y divide-b2c-border">
              <thead className={b2cTableThead}>
                <tr>
                  <th className={`px-6 py-3 text-left ${b2cTableHeader}`}>#</th>
                  <th className={`px-6 py-3 text-left ${b2cTableHeader}`}>Date</th>
                  <th className={`px-6 py-3 text-left ${b2cTableHeader}`}>Session</th>
                  <th className={`px-6 py-3 text-left ${b2cTableHeader}`}>Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-b2c-border bg-osce-surface">
                {attempts.map((attempt, index) => (
                  <tr key={attempt.id} className="transition-colors hover:bg-b2c-surface-muted">
                    <td className={cn("whitespace-nowrap px-6 py-4", b2cTableCell)}>
                      <span className="rounded-full bg-b2c-secondary px-3 py-1 text-osce-data text-osce-ink-900">
                        {index + 1}
                      </span>
                    </td>
                    <td className={cn("whitespace-nowrap px-6 py-4", b2cTableCell)}>
                      {formatAttemptDate(attempt.created_at)}
                    </td>
                    <td className={cn("whitespace-nowrap px-6 py-4", b2cTableCell)}>
                      {attempt.exam_code.toUpperCase()} · {kindLabel(attempt.kind)}
                    </td>
                    <td className={cn("whitespace-nowrap px-6 py-4", b2cTableCell)}>
                      <Link
                        href={hrefFor(`/transcripts/${attempt.id}`)}
                        className="group flex cursor-pointer items-center space-x-2"
                      >
                        <span className="font-medium text-osce-accent">View details</span>
                        <HiOutlineArrowRight
                          className="h-4 w-4 text-osce-accent transition-transform group-hover:translate-x-1"
                          aria-hidden
                        />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </AsyncBoundary>
    </div>
  );
}
