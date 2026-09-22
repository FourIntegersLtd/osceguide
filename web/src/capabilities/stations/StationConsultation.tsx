"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { AsyncBoundary } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities/SurfaceContext";
import { AttemptRunner, createAttempt, useExtraReadingPercent, withExtraReadingTime } from "@/capabilities/attempt-runner";
import { findLibraryStation, listExams } from "@/capabilities/stations/api";
import { stationHref } from "@/capabilities/stations/routes";

/**
 * Practising one station from the library.
 *
 * Everything between "start" and "ended" is `capabilities/attempt-runner` —
 * the reading clock, the microphone check, the room, the patient tile, the
 * wind-down cue and the hang-up. All this adds is the one call that differs
 * between the ways a station can be reached: free practice posts to
 * `/attempts` with the station's version id, where a mock posts to its set
 * entry and a circuit starts a slot. That is the whole reason the runner is a
 * capability rather than three implementations, and it is why this file is
 * sixty lines instead of the old client's four hundred.
 */
export function StationConsultation({ stationId }: { stationId: string }) {
  const router = useRouter();
  const { hrefFor } = useSurface();
  const extraReadingPercent = useExtraReadingPercent();

  const station = useAsync((signal) => findLibraryStation(stationId, signal), [stationId]);
  const exams = useAsync(async (signal) => (await listExams(signal)).items, []);
  const exam = exams.data?.find((item) => item.code === station.data?.exam_code) ?? null;

  const start = useCallback(async () => {
    const found = station.data;
    if (!found) throw new Error("That station is no longer available.");
    const attempt = await createAttempt({
      examCode: found.exam_code,
      kind: "practice",
      stationVersionId: found.version_id,
    });
    return { id: attempt.id };
  }, [station.data]);

  const onEnded = useCallback(
    (attemptId: string) => {
      // Straight to the result, which waits for scoring. Dropping somebody
      // back on the library is how the old client lost people between
      // finishing a station and reading their feedback.
      router.push(hrefFor(`/attempts/${attemptId}`));
    },
    [router, hrefFor],
  );

  return (
    <div className="flex flex-col gap-4">
      <AsyncBoundary
        state={station}
        empty={{
          title: "We could not find that station",
          description: "It may have been withdrawn, or replaced by a newer version.",
        }}
      >
        {(found) => (
          <>
            <Link
              href={stationHref(hrefFor, found.id)}
              className="text-osce-meta text-b2c-text-muted hover:text-osce-ink-900"
            >
              Leave and go back to the station
            </Link>
            <AttemptRunner
              start={start}
              onEnded={onEnded}
              stationTitle={found.title}
              readingSeconds={withExtraReadingTime(exam?.default_reading_seconds ?? 0, extraReadingPercent)}
              simulationSeconds={exam?.default_simulation_seconds ?? 600}
            />
          </>
        )}
      </AsyncBoundary>
    </div>
  );
}
