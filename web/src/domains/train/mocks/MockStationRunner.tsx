"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { AsyncBoundary } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { AttemptRunner } from "@/capabilities/attempt-runner";
import { listExams } from "@/capabilities/stations";
import { loadStationCatalogue, readSet, startSetAttempt } from "@/domains/train/api";

/**
 * Run one station from a session.
 *
 * This is the whole of what Train adds to the shared runner: it knows how a
 * consumer is permitted to start — through their set entry, which counts the
 * attempt against the exam's limit in SQL inside the attempt's own transaction
 * — and where to send them afterwards.
 */
export function MockStationRunner({ setId, entryId }: { setId: string; entryId: string }) {
  const router = useRouter();
  const { hrefFor } = useSurface();

  const context = useAsync(
    async (signal) => {
      const set = await readSet(setId, signal);
      const entry = (set.entries ?? []).find((item) => item.id === entryId) ?? null;
      const [library, exams] = await Promise.all([
        loadStationCatalogue(set.exam_code, signal),
        listExams(signal),
      ]);
      const station = entry
        ? library.find((item) => item.version_id === entry.station_version_id)
        : undefined;
      const exam = exams.items.find((item) => item.code === set.exam_code) ?? null;
      return { set, station, exam };
    },
    [setId, entryId],
  );

  const start = useCallback(async () => {
    const started = await startSetAttempt(setId, entryId);
    return { id: started.attempt_id };
  }, [setId, entryId]);

  const onEnded = useCallback(
    (attemptId: string) => {
      // Straight to the result, which polls until scoring lands. Dropping the
      // candidate back on the list is how the old client lost people between
      // finishing and reading their feedback.
      router.push(hrefFor(`/attempts/${attemptId}`));
    },
    [router, hrefFor],
  );

  return (
    <AsyncBoundary state={context}>
      {({ station, exam }) => (
        <AttemptRunner
          start={start}
          onEnded={onEnded}
          stationTitle={station?.title ?? "Station"}
          readingSeconds={exam?.default_reading_seconds ?? 0}
          simulationSeconds={exam?.default_simulation_seconds ?? 600}
          patientName="Your patient"
        />
      )}
    </AsyncBoundary>
  );
}
