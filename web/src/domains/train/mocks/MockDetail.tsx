"use client";

import { useState } from "react";
import { HiOutlineLockClosed } from "react-icons/hi2";
import {
  AsyncBoundary,
  B2CEmptyState,
  B2CPageHeader,
  Button,
  ButtonLink,
  productTokens,
} from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { useAsync } from "@/foundation/hooks";
import { useSession } from "@/foundation/session";
import { practiceTimers } from "@/capabilities/attempt-runner";
import { hasCode } from "@/foundation/platform-client";
import { listExams } from "@/capabilities/stations";
import { readSet } from "@/domains/train/api";
import { MockRules } from "@/domains/train/mocks/MockRules";
import { MockStationsTable, type StationRow } from "@/domains/train/mocks/MockStationsTable";
import { B2CHero } from "@/foundation/ui/B2CHero";
import { EXAM_NOT_OFFERED, canStartSession, entriesInOrder, sessionMinutes, stationLabel } from "@/domains/train/mocks/model";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-[104px] rounded-osce-lg border border-osce-border bg-osce-surface px-4 py-3 text-center">
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
  const { session } = useSession();
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
      const exams = await listExams(signal);
      // The server names a station only once it has been sat; before that it is "Station N".
      const rows: StationRow[] = entriesInOrder(set).map((entry, index) => ({
        entry,
        title: stationLabel(entry, index),
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
          // The person's own timers, when their access arrangement is on, replace the exam's.
          const timers = practiceTimers(session?.user, {
            readingSeconds: exam?.default_reading_seconds ?? 180,
            simulationSeconds: exam?.default_simulation_seconds ?? 720,
          });
          const readingMinutes = Math.round(timers.readingSeconds / 60);
          const simulationMinutes = Math.round(timers.simulationSeconds / 60);
          const duration = sessionMinutes(set.total_entries, exam ? timers : null);
          const first = rows[0]?.entry ?? null;
          const startsHere = canStartSession({ examOffered: exam !== null, attempted, locked: set.locked });
          // A session with no stations has nowhere to start; the button stays inert.
          const canStart = micReady && first !== null;

          return (
            <div className="space-y-6">
              <B2CPageHeader
                back={{ href: hrefFor("/mocks/list"), label: "Sessions" }}
                title={set.name}
                /* Hidden for learners: only admins edit or delete sessions (2026-10-14). Edit link:
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
                */
              />

              <B2CHero
                title={`For each station: ${readingMinutes} minutes reading, then ${simulationMinutes} minutes with the patient`}
                aside={
                  <>
                    <Stat label="Stations" value={String(set.total_entries)} />
                    <Stat label="Duration" value={`${duration} min`} />
                  </>
                }
                action={
                  startsHere ? (
                    first && canStart ? (
                      <ButtonLink
                        href={`${hrefFor(`/mocks/${set.id}/stations/${first.id}`)}?action=attempt`}
                        variant="primary"
                        size="md"
                      >
                        Start session
                      </ButtonLink>
                    ) : (
                      <Button variant="primary" size="md" disabled>
                        {micReady ? "Start session" : "Allow your microphone to start"}
                      </Button>
                    )
                  ) : undefined
                }
              >
                Sit them back to back. Feedback for each station is prepared while you sit the next.
              </B2CHero>

              {attempted ? (
                <MockStationsTable
                  set={set}
                  rows={rows}
                  attemptLimit={exam?.station_attempt_limit ?? null}
                />
              ) : set.locked ? (
                <B2CEmptyState
                  icon={HiOutlineLockClosed}
                  title="Nothing to review in this session"
                  description="This session is from a past subscription. It was never attempted, so there is no feedback or transcript to review, and reattempts are not available."
                />
              ) : exam === null ? (
                <B2CEmptyState
                  icon={HiOutlineLockClosed}
                  title={EXAM_NOT_OFFERED.title}
                  description={EXAM_NOT_OFFERED.description}
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
