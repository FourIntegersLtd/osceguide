"use client";

import { HiOutlineLockClosed } from "react-icons/hi2";
import {
  AsyncBoundary,
  B2CEmptyState,
  B2CPageHeader,
  B2CPanelCard,
  B2CPanelCardBody,
  productTokens,
} from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { listExams } from "@/capabilities/stations";
import { loadStationCatalogue, readDashboard, readSet } from "@/domains/train/api";
import { MockComplete } from "@/domains/train/mocks/MockComplete";
import { MockRules } from "@/domains/train/mocks/MockRules";
import { MockStationsTable, type StationRow } from "@/domains/train/mocks/MockStationsTable";
import { entriesInOrder, sessionMinutes } from "@/domains/train/mocks/model";

/**
 * One session: its rules before you start, its stations once you have.
 *
 * The old screen asked the same `getMockById` twice — once to decide whether
 * the session had been attempted and once for the session itself — and so
 * rendered two loading states in sequence. One request answers both here,
 * because "attempted" is a fact about the set rather than a second question.
 */
export function MockDetail({ setId }: { setId: string }) {
  const { hrefFor } = useSurface();

  const state = useAsync(
    async (signal) => {
      const set = await readSet(setId, signal);
      // Entries carry a station version id and no title, so the library is the
      // lookup. One request for the exam beats one per entry.
      const [library, exams, dashboard] = await Promise.all([
        loadStationCatalogue(set.exam_code, signal),
        listExams(signal),
        readDashboard(signal),
      ]);
      const titles = new Map(library.map((station) => [station.version_id, station.title]));
      const rows: StationRow[] = entriesInOrder(set).map((entry) => ({
        entry,
        title: titles.get(entry.station_version_id) ?? "Station",
      }));
      const exam = exams.items.find((item) => item.code === set.exam_code) ?? null;
      const stationsCompleted = (dashboard.progress ?? []).reduce(
        (total, progress) => total + progress.evaluated,
        0,
      );
      return { set, rows, exam, stationsCompleted };
    },
    [setId],
  );

  return (
    <div className={productTokens.b2cPageColumn}>
      <AsyncBoundary state={state}>
        {({ set, rows, exam, stationsCompleted }) => {
          const attempted = set.attempted_entries > 0;
          const duration = sessionMinutes(
            set.total_entries,
            exam
              ? {
                  readingSeconds: exam.default_reading_seconds,
                  simulationSeconds: exam.default_simulation_seconds,
                }
              : null,
          );

          return (
            <div className="space-y-6">
              <B2CPageHeader title={set.name} back={{ href: hrefFor("/mocks") }} />

              {set.completed_at !== null && !set.locked ? (
                <MockComplete set={set} rows={rows} stationsCompleted={stationsCompleted} />
              ) : null}

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 lg:w-2/3">
                <B2CPanelCard>
                  <B2CPanelCardBody>
                    <p className={productTokens.b2cFieldLabel}>Duration</p>
                    <p className={`${productTokens.b2cFieldValue} mt-1 text-osce-body`}>
                      {duration} min
                    </p>
                  </B2CPanelCardBody>
                </B2CPanelCard>
                <B2CPanelCard>
                  <B2CPanelCardBody>
                    <p className={productTokens.b2cFieldLabel}>Stations</p>
                    <p className={`${productTokens.b2cFieldValue} mt-1 text-osce-body`}>
                      {set.total_entries}
                    </p>
                  </B2CPanelCardBody>
                </B2CPanelCard>
              </div>

              <div>
                {attempted ? (
                  <MockStationsTable
                    set={set}
                    rows={rows}
                    attemptLimit={exam?.station_attempt_limit ?? 3}
                  />
                ) : set.locked ? (
                  <B2CEmptyState
                    icon={HiOutlineLockClosed}
                    title="Nothing to review in this session"
                    description="This session is from a past subscription. It was never attempted, so there is no feedback or transcript to review, and reattempts aren't available."
                  />
                ) : (
                  <MockRules set={set} entry={rows[0]?.entry ?? null} exam={exam} />
                )}
              </div>
            </div>
          );
        }}
      </AsyncBoundary>
    </div>
  );
}
