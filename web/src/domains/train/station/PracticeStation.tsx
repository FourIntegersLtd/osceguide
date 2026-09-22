"use client";

import { useCallback } from "react";
import { AsyncBoundary } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { useCurrentExam } from "@/foundation/session";
import { createAttempt } from "@/capabilities/attempt-runner";
import { findLibraryStation, listExams } from "@/capabilities/stations";
import { StationScreen } from "@/capabilities/station-runner/StationScreen";
import type { StationStep } from "@/capabilities/station-runner/StationChrome";
import type { StationAction } from "@/capabilities/station-runner/useStationAttempt";

/**
 * One station from the library, sat on its own.
 *
 * The same screen as a session's station, with two differences that are facts
 * about free practice rather than options: there is no "next station" because
 * there is no session, and there is no attempts pill because the limit is
 * counted per set entry rather than per station.
 */
export function PracticeStation({
  stationId,
  action = "attempt",
  step,
  attemptId,
}: {
  stationId: string;
  action?: StationAction;
  step?: StationStep;
  attemptId?: string | null;
}) {
  const { hrefFor } = useSurface();
  const { code: currentExam } = useCurrentExam();

  const context = useAsync(
    async (signal) => {
      const station = await findLibraryStation(stationId, signal);
      const exams = await listExams(signal);
      const exam = exams.items.find((item) => item.code === station?.exam_code) ?? null;
      return { station, exam };
    },
    [stationId],
  );

  /*
   * Hoisted out of the render callback: a hook inside one runs conditionally,
   * which is the rule this would break. The station's version id comes from
   * the loaded context, so this reads it off the state rather than the child's
   * argument.
   */
  const versionId = context.data?.station?.version_id ?? null;
  const examCode = context.data?.station?.exam_code ?? currentExam ?? "";
  const create = useCallback(async () => {
    const started = await createAttempt({
      examCode,
      kind: "practice",
      stationVersionId: versionId,
    });
    return { id: started.id };
  }, [examCode, versionId]);

  return (
    <AsyncBoundary state={context}>
      {({ station, exam }) => (
        <StationScreen
          source={{ kind: "practice", stationId }}
          action={action}
          step={step}
          attemptId={attemptId}
          stationVersionId={station?.version_id ?? null}
          examCode={station?.exam_code ?? currentExam ?? ""}
          readingSeconds={exam?.default_reading_seconds ?? 0}
          simulationSeconds={exam?.default_simulation_seconds ?? 600}
          index={0}
          total={1}
          attemptsUsed={null}
          attemptLimit={null}
          createAttempt={create}
          nextHref={null}
          completeHref={hrefFor("/stations")}
          flagStationId={station?.id ?? stationId}
        />
      )}
    </AsyncBoundary>
  );
}
