import type { ReactNode } from "react";
import { boardChip } from "@/foundation/ui/boardKit";
import {
  TraineeHero,
  TraineeList,
  TraineeRow,
} from "@/domains/assess/trainee/traineeBoard";
import {
  stationScoreLabel,
  type TraineeResult,
} from "@/domains/assess/trainee/api";

/**
 * The outcome and by-station sections of a result, as the candidate sees them.
 *
 * Shared by the candidate's own page and the staff preview, so the two cannot drift.
 * It draws whatever it is given: whether a result may be shown at all is the caller's
 * call (the candidate's page refuses an unreleased one; the preview exists to show it).
 */
export function ResultView({
  result,
  actions,
}: {
  result: TraineeResult;
  actions?: ReactNode;
}) {
  return (
    <>
      <TraineeHero
        eyebrow="Outcome"
        title={
          result.assessment_score != null
            ? `${outcomeLabel(result.assessment_outcome)}, ${result.assessment_score.toFixed(1)} / 100`
            : outcomeLabel(result.assessment_outcome)
        }
        size="xl"
        action={actions}
      >
        {result.rationale ? (
          <span className="whitespace-pre-wrap">{result.rationale}</span>
        ) : null}
      </TraineeHero>
      {result.stations && result.stations.length > 0 ? (
        <TraineeList title="By station">
          {result.stations.map((station) => {
            const label = stationScoreLabel(station);
            return (
              <TraineeRow
                key={station.slot_id}
                title={station.station_title ?? "Station"}
              >
                <span
                  className={boardChip(
                    /pass/i.test(label) ? "ok" : "neutral",
                  )}
                >
                  {label}
                </span>
              </TraineeRow>
            );
          })}
        </TraineeList>
      ) : null}
    </>
  );
}

function outcomeLabel(outcome: string | null | undefined): string {
  if (!outcome) return "Recorded";
  return outcome
    .replace(/_/g, " ")
    .replace(/^\w/, (letter) => letter.toUpperCase());
}
