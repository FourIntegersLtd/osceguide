"use client";

import { useState } from "react";
import { HiOutlineLockClosed } from "react-icons/hi2";
import {
  AsyncBoundary,
  B2CEmptyState,
  B2CPageHeader,
  ButtonLink,
  cn,
  productTokens,
} from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { useAsync } from "@/foundation/hooks";
import { hasCode } from "@/foundation/platform-client";
import { listExams } from "@/capabilities/stations";
import { loadStationCatalogue, readSet } from "@/domains/train/api";
import { MockRules } from "@/domains/train/mocks/MockRules";
import { MockStationsTable, type StationRow } from "@/domains/train/mocks/MockStationsTable";
import { B2CHero } from "@/foundation/ui/B2CHero";
import { entriesInOrder, sessionMinutes } from "@/domains/train/mocks/model";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-[104px] rounded-osce-lg border border-osce-border bg-osce-surface px-4 py-3">
      <p className="text-osce-meta text-b2c-text-muted">{label}</p>
      <p className="mt-0.5 text-osce-data font-semibold tabular-nums text-osce-ink-900">{value}</p>
    </div>
  );
}

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
  const [micReady, setMicReady] = useState(false);
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
                <B2CPageHeader
                  back={{ href: hrefFor("/mocks/list"), label: "Sessions" }}
                  title="Session not found"
                />
                <p className="text-osce-body text-b2c-text-muted">
                  It may have been deleted, or it belongs to another account.
                </p>
              </>
            );
          }
          const { set, rows, exam } = loaded;
          const attempted = set.attempted_entries > 0;
          const readingMinutes = Math.round((exam?.default_reading_seconds ?? 180) / 60);
          const simulationMinutes = Math.round((exam?.default_simulation_seconds ?? 720) / 60);
          const duration = sessionMinutes(
            set.total_entries,
            exam
              ? {
                  readingSeconds: exam.default_reading_seconds,
                  simulationSeconds: exam.default_simulation_seconds,
                }
              : null,
          );
          const stationsLabel = `${set.total_entries} ${set.total_entries === 1 ? "station" : "stations"}`;
          const first = rows[0]?.entry ?? null;
          const startsHere = !attempted && !set.locked;
          // A session with no stations has nowhere to start; the button stays inert.
          const canStart = micReady && first !== null;

          return (
            <div className="mx-auto max-w-osce-page space-y-6">
              <B2CPageHeader
                back={{ href: hrefFor("/mocks/list"), label: "Sessions" }}
                title={set.name}
                action={
                  set.locked ? undefined : (
                    <ButtonLink
                      href={hrefFor(`/mocks/${set.id}/update`)}
                      variant="secondary"
                      size="md"
                    >
                      Edit
                    </ButtonLink>
                  )
                }
              />

              <B2CHero
                eyebrow={`${duration} minutes, ${stationsLabel}`}
                title={`For each station: ${readingMinutes} minutes reading, then ${simulationMinutes} minutes with the patient`}
                aside={
                  <>
                    <Stat label="Duration" value={`${duration} min`} />
                    <Stat label="Stations" value={String(set.total_entries)} />
                  </>
                }
                action={
                  startsHere ? (
                    <ButtonLink
                      href={
                        first
                          ? `${hrefFor(`/mocks/${set.id}/stations/${first.id}`)}?action=attempt`
                          : hrefFor(`/mocks/${set.id}`)
                      }
                      variant="primary"
                      size="md"
                      aria-disabled={!canStart}
                      className={cn(!canStart && "pointer-events-none opacity-60")}
                    >
                      {micReady ? "Start session" : "Allow your microphone to start"}
                    </ButtonLink>
                  ) : undefined
                }
              >
                Sit them back to back. Feedback for each station arrives while you sit the next.
              </B2CHero>

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
                  description="This session is from a past subscription. It was never attempted, so there is no feedback or transcript to review, and reattempts are not available."
                />
              ) : (
                <MockRules exam={exam} onMicReadyChange={setMicReady} />
              )}
            </div>
          );
        }}
      </AsyncBoundary>
    </div>
  );
}
