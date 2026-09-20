"use client";

import { PracticeOptions } from "@/capabilities/peer-practice/PracticeOptions";

import { HiOutlineArrowRight } from "react-icons/hi2";
import { AsyncBoundary, B2CPanelCard, B2CPanelCardBody, B2CPanelCardHeader, LoadingSpinner } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { listMyAttempts, type AttemptHistoryItem } from "@/capabilities/attempt-runner";
import { loadStationCatalogue, readDashboard, readSet } from "@/domains/train/api";
import { MockComplete } from "@/domains/train/mocks/MockComplete";
import { entriesInOrder } from "@/domains/train/mocks/model";
import type { StationRow } from "@/domains/train/mocks/MockStationsTable";

/**
 * The end of a session: what was sat, and whether it has been marked yet.
 *
 * The retiring client's `/mocks/[mockId]/complete`, restored. It was dropped
 * in the port because the congratulations panel had been folded into the
 * session page — which was right for the panel and wrong for the moment: the
 * last station's "Complete session" had nowhere to go, and a candidate who had
 * just finished eight consultations was dropped back on a list.
 *
 * What it adds over the panel is the feedback status list. Marking runs behind
 * the session, so at this moment some stations are marked and some are still
 * being scored, and this is the screen that says which.
 */
export function MockEnd({ setId }: { setId: string }) {
  const { hrefFor } = useSurface();

  const state = useAsync(
    async (signal) => {
      const set = await readSet(setId, signal);
      const entries = entriesInOrder(set);
      const [library, dashboard, ...perEntry] = await Promise.all([
        loadStationCatalogue(set.exam_code, signal),
        readDashboard(signal),
        ...entries.map((entry) =>
          listMyAttempts({ setEntryId: entry.id, limit: 5 }, signal).catch(() => ({
            items: [] as AttemptHistoryItem[],
          })),
        ),
      ]);
      const titles = new Map(library.map((station) => [station.version_id, station.title]));
      const rows: StationRow[] = entries.map((entry) => ({
        entry,
        title: titles.get(entry.station_version_id) ?? "Station",
      }));
      const attempts = new Map(entries.map((entry, index) => [entry.id, perEntry[index]?.items ?? []]));
      const stationsCompleted = (dashboard.progress ?? []).reduce(
        (total, progress) => total + progress.evaluated,
        0,
      );
      return { set, rows, attempts, stationsCompleted };
    },
    [setId],
  );

  return (
    <AsyncBoundary state={state}>
      {({ set, rows, attempts, stationsCompleted }) => (
        <div className="space-y-6">
          <PracticeOptions />
          <MockComplete set={set} rows={rows} stationsCompleted={stationsCompleted} />

          <B2CPanelCard className="mt-0">
            <B2CPanelCardHeader>Feedback status</B2CPanelCardHeader>
            <B2CPanelCardBody>
              <ul className="divide-y divide-b2c-border">
                {rows.map((row, index) => {
                  const sat = attempts.get(row.entry.id) ?? [];
                  const marked = sat.find((item) => item.has_result);
                  const running = sat.length > 0 && !marked;

                  return (
                    <li
                      key={row.entry.id}
                      className="flex flex-wrap items-center justify-between gap-2 py-3"
                    >
                      <span className="min-w-0 truncate text-osce-body text-osce-ink-900">
                        {`Station ${index + 1}: ${row.title}`}
                      </span>
                      {marked ? (
                        <a
                          href={`${hrefFor(`/mocks/${setId}/stations/${row.entry.id}`)}?action=review&tab=feedback`}
                          className="inline-flex items-center gap-1.5 text-osce-body text-osce-accent hover:text-osce-accent-hover"
                        >
                          Review feedback
                          <HiOutlineArrowRight className="h-4 w-4" aria-hidden />
                        </a>
                      ) : running ? (
                        <span className="inline-flex items-center gap-2 text-osce-meta text-b2c-text-muted">
                          <LoadingSpinner /> Marking station {index + 1}…
                        </span>
                      ) : (
                        <span className="text-osce-meta text-b2c-text-muted">Not attempted</span>
                      )}
                    </li>
                  );
                })}
              </ul>
            </B2CPanelCardBody>
          </B2CPanelCard>
        </div>
      )}
    </AsyncBoundary>
  );
}
