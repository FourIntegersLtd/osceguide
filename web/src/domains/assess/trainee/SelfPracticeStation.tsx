"use client";

import Link from "next/link";
import { useCallback } from "react";
import { Alert, AsyncBoundary } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { createAttempt } from "@/capabilities/attempt-runner";
import { listExams } from "@/capabilities/stations";
import { StationScreen } from "@/capabilities/station-runner/StationScreen";
import type { StationStep } from "@/capabilities/station-runner/StationChrome";
import type { StationAction } from "@/capabilities/station-runner/useStationAttempt";
import { listOrgStations } from "@/domains/assess/trainee/api";
import { practisableStation } from "@/domains/assess/trainee/practisableStation";

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
  const practiceHref = hrefFor("/trainee/practice");

  const context = useAsync(
    async (signal) => {
      const stations = await listOrgStations(orgSlug, signal);
      const station = practisableStation(stations, stationId);
      const exams = await listExams(signal);
      const exam = station
        ? (exams.items.find((item) => item.code === station.exam_code) ?? null)
        : null;
      return { station, exam };
    },
    [orgSlug, stationId],
  );

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
          <>
            {action === "attempt" && !attemptId ? (
              <header className="space-y-1">
                <h1 className="text-osce-title font-semibold text-ink">
                  {station.title}
                </h1>
                <p className="text-osce-body text-ink-muted">
                  Nothing here is marked for the record.
                </p>
              </header>
            ) : null}
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
              completeHref={practiceHref}
              backHref={practiceHref}
            />
          </>
        ) : (
          <Alert tone="warning" title="This station is not available">
            <p>
              It may have been withdrawn, is not published yet, or belongs to
              another organisation.
            </p>
            <Link
              href={practiceHref}
              className="mt-3 inline-block font-semibold underline"
            >
              Back to practice
            </Link>
          </Alert>
        )
      }
    </AsyncBoundary>
  );
}
