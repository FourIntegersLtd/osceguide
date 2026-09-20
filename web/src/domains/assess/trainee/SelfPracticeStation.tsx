"use client";

import { useCallback } from "react";
import { AsyncBoundary } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { createAttempt } from "@/capabilities/attempt-runner";
import { listExams } from "@/capabilities/stations";
import { StationScreen } from "@/domains/train/station/StationScreen";
import type { StationStep } from "@/domains/train/station/StationChrome";
import type { StationAction } from "@/domains/train/station/useStationAttempt";
import { listOrgStations, type OrgStation } from "@/domains/assess/trainee/api";

/**
 * One org station sat with the same four-step runner as consumer practice.
 */
export function SelfPracticeStation({
  orgSlug,
  stationId,
  action = "attempt",
  step,
  attemptId,
}: {
  orgSlug: string;
  stationId: string;
  action?: StationAction;
  step?: StationStep;
  attemptId?: string | null;
}) {
  const { hrefFor } = useSurface();

  const context = useAsync(
    async (signal) => {
      const stations = await listOrgStations(orgSlug, signal);
      const station = stations.find((row) => row.id === stationId) ?? null;
      const exams = await listExams(signal);
      const exam = station
        ? exams.items.find((item) => item.code === station.exam_code) ?? null
        : null;
      return { station, exam };
    },
    [orgSlug, stationId],
  );

  const versionId = context.data?.station?.current_version_id ?? null;
  const examCode = context.data?.station?.exam_code ?? "";

  const create = useCallback(async () => {
    const row = context.data?.station;
    if (!row) throw new Error("That station is no longer available.");
    const started = await createAttempt({
      examCode: row.exam_code,
      kind: "self_practice",
      stationVersionId: row.current_version_id,
    });
    return { id: started.id };
  }, [context.data?.station]);

  return (
    <AsyncBoundary state={context}>
      {({ station, exam }) =>
        station ? (
          <StationScreen
            source={{ kind: "self_practice", orgSlug, stationId }}
            action={action}
            step={step}
            attemptId={attemptId}
            stationVersionId={station.current_version_id}
            examCode={station.exam_code}
            readingSeconds={exam?.default_reading_seconds ?? 0}
            simulationSeconds={exam?.default_simulation_seconds ?? 600}
            index={0}
            total={1}
            attemptsUsed={null}
            attemptLimit={null}
            createAttempt={create}
            nextHref={null}
            completeHref={hrefFor("/trainee/practice")}
          />
        ) : null
      }
    </AsyncBoundary>
  );
}
