"use client";

import { useCallback } from "react";
import { Alert, AsyncBoundary, Button } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { useCurrentExam } from "@/foundation/session";
import { createAttempt } from "@/capabilities/attempt-runner";
import { hasCode } from "@/foundation/platform-client/errors";
import {
  listExams,
  readLibraryStation,
  StationNotFound,
  StationNotInPlanGate,
} from "@/capabilities/stations";
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
      const station = await readLibraryStation(stationId, signal);
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
    <AsyncBoundary
      state={context}
      failure={(error, retry) =>
        hasCode(error, "station_not_in_plan") ? (
          <StationNotInPlanGate />
        ) : (
          <Alert tone="danger" title="That did not load">
            <p>{error.message || "Something went wrong."}</p>
            <Button variant="secondary" size="sm" className="mt-3" onClick={retry}>
              Try again
            </Button>
          </Alert>
        )
      }
    >
      {({ station, exam }) =>
        station === null ? (
          // The link named a station this person cannot read. The runner is not
          // drawn against nothing: it would show a clock with no brief behind it.
          <StationNotFound />
        ) : (
          <StationScreen
            source={{ kind: "practice", stationId }}
            action={action}
            step={step}
            attemptId={attemptId}
            stationVersionId={station.version_id}
            examCode={station.exam_code}
            readingSeconds={exam?.default_reading_seconds ?? 0}
            simulationSeconds={exam?.default_simulation_seconds ?? 600}
            index={0}
            total={1}
            attemptsUsed={null}
            attemptLimit={null}
            createAttempt={create}
            nextHref={null}
            /*
             * Not `/stations` — the library browse screen is institution nav
             * only (`registry.test.ts` pins that), so it has no route on this
             * arm and that href 404s. This screen is reached from the
             * flagged-stations tab of `/mocks`, so that is where finishing
             * one goes back to.
             */
            completeHref={hrefFor("/mocks")}
            flagStationId={station.id}
          />
        )
      }
    </AsyncBoundary>
  );
}
