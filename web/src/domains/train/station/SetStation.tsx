"use client";

import { useCallback } from "react";
import { AsyncBoundary } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { listExams } from "@/capabilities/stations";
import { flagSetEntry, loadStationCatalogue, readSet, startSetAttempt } from "@/domains/train/api";
import { StationScreen } from "@/capabilities/station-runner/StationScreen";
import type { StationStep } from "@/capabilities/station-runner/StationChrome";
import type { StationAction } from "@/capabilities/station-runner/useStationAttempt";
import { entriesInOrder } from "@/domains/train/mocks/model";

/**
 * A station of a practice session.
 *
 * All this adds to the shared screen is how a consumer is permitted to start —
 * through their set entry, which counts the attempt against the exam's limit in
 * SQL inside the attempt's own transaction — and where the session goes next.
 */
export function SetStation({
  setId,
  entryId,
  action = "attempt",
  step,
  attemptId,
}: {
  setId: string;
  entryId: string;
  action?: StationAction;
  step?: StationStep;
  attemptId?: string | null;
}) {
  const { hrefFor } = useSurface();

  const context = useAsync(
    async (signal) => {
      const set = await readSet(setId, signal);
      const [library, exams] = await Promise.all([
        loadStationCatalogue(set.exam_code, signal),
        listExams(signal),
      ]);
      const entries = entriesInOrder(set);
      const index = entries.findIndex((item) => item.id === entryId);
      const entry = index >= 0 ? entries[index] : null;
      const station = entry
        ? library.find((item) => item.version_id === entry.station_version_id)
        : undefined;
      const exam = exams.items.find((item) => item.code === set.exam_code) ?? null;
      const next = index >= 0 ? entries[index + 1] : undefined;
      return { set, entries, index, entry, station, exam, next };
    },
    [setId, entryId],
  );

  const create = useCallback(async () => {
    const started = await startSetAttempt(setId, entryId);
    // The counter moved on the server; re-read it so the Attempts pill follows.
    context.reload();
    return { id: started.attempt_id };
  }, [setId, entryId, context]);

  return (
    <AsyncBoundary state={context}>
      {({ set, entries, index, entry, station, exam, next }) => (
        <StationScreen
          source={{ kind: "set", setId, entryId }}
          action={action}
          step={step}
          attemptId={attemptId}
          stationVersionId={entry?.station_version_id ?? station?.version_id ?? null}
          examCode={set.exam_code}
          readingSeconds={exam?.default_reading_seconds ?? 0}
          simulationSeconds={exam?.default_simulation_seconds ?? 600}
          index={Math.max(index, 0)}
          total={entries.length}
          attemptsUsed={entry?.attempts ?? null}
          attemptLimit={exam?.station_attempt_limit ?? null}
          flagStationId={station?.id ?? null}
          comeBack={
            entry
              ? {
                  initial: Boolean(entry.flagged_at),
                  save: async (flagged) => {
                    await flagSetEntry(setId, entryId, flagged);
                  },
                }
              : null
          }
          createAttempt={create}
          backHref={hrefFor(`/mocks/${setId}`)}
          nextHref={next ? hrefFor(`/mocks/${setId}/stations/${next.id}`) : null}
          completeHref={hrefFor(`/mocks/${setId}/complete`)}
        />
      )}
    </AsyncBoundary>
  );
}
