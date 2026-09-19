"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { AsyncBoundary } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { AttemptRunner } from "@/capabilities/attempt-runner";
import { browseLibrary } from "@/capabilities/stations";
import { readSet, startSetAttempt } from "@/domains/train/api";
import { useExam } from "@/domains/train/useExam";

/**
 * Run one station from a mock.
 *
 * This is the whole of what Train adds to the shared runner: it knows how a
 * consumer is permitted to start (through their set entry, which counts the
 * attempt against the exam's limit) and where to send them afterwards.
 */
export function MockStationRunner({ setId, entryId }: { setId: string; entryId: string }) {
  const router = useRouter();
  const { hrefFor } = useSurface();

  const context = useAsync(
    async (signal) => {
      const set = await readSet(setId, signal);
      const entry = (set.entries ?? []).find((item) => item.id === entryId) ?? null;
      const library = await browseLibrary({ examCode: set.exam_code, limit: 200 }, signal);
      const station = entry
        ? library.items.find((item) => item.version_id === entry.station_version_id)
        : undefined;
      return { set, station };
    },
    [setId, entryId],
  );

  const exam = useExam(context.data?.set.exam_code);

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
      {({ station }) => (
        <AsyncBoundary state={exam}>
          {(examData) => (
            <AttemptRunner
              start={start}
              onEnded={onEnded}
              stationTitle={station?.title ?? "Station"}
              readingSeconds={examData?.default_reading_seconds ?? 0}
              simulationSeconds={examData?.default_simulation_seconds ?? 600}
              patientName="Your patient"
            />
          )}
        </AsyncBoundary>
      )}
    </AsyncBoundary>
  );
}
