"use client";

import { HiOutlineLockClosed } from "react-icons/hi2";
import { RiSpeakLine } from "react-icons/ri";
import {
  AsyncBoundary,
  B2CEmptyState,
  Back,
  B2CPageHeader,
  B2CPanelCard,
  B2CPanelCardBody,
  productTokens,
} from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { hasCode } from "@/foundation/platform-client";
import { listExams } from "@/capabilities/stations";
import { loadStationCatalogue, readSet } from "@/domains/train/api";
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
  const state = useAsync(
    async (signal) => {
      // Someone else's id, or one since deleted, is the old screen's "No mock
      // found" rather than an error with a retry that can never succeed.
      const set = await readSet(setId, signal).catch((cause: unknown) => {
        if (hasCode(cause, "set_not_found")) return null;
        throw cause;
      });
      if (set === null) return null;
      // Entries carry a station version id and no title, so the library is the
      // lookup. One request for the exam beats one per entry.
      const [library, exams] = await Promise.all([
        loadStationCatalogue(set.exam_code, signal),
        listExams(signal),
      ]);
      const titles = new Map(library.map((station) => [station.version_id, station.title]));
      const rows: StationRow[] = entriesInOrder(set).map((entry) => ({
        entry,
        title: titles.get(entry.station_version_id) ?? "Station",
      }));
      const exam = exams.items.find((item) => item.code === set.exam_code) ?? null;
      return { set, rows, exam };
    },
    [setId],
  );

  return (
    <div className={productTokens.b2cPageColumn}>
      <AsyncBoundary state={state}>
        {(loaded) => {
          if (loaded === null) {
            return (
              <>
                <Back />
                <p className="mt-4 text-osce-body text-b2c-text-muted">No mock found</p>
              </>
            );
          }
          const { set, rows, exam } = loaded;
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
            <div className="mx-auto max-w-osce-page space-y-6">
              <Back />

              <B2CPageHeader title={set.name} icon={RiSpeakLine} />

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
