import type { ReactNode } from "react";
import { B2CGroupedRow, B2CGroupedSection, B2CHero, Badge } from "@/foundation/ui";
import { stationScoreLabel, type TraineeResult } from "@/domains/assess/trainee/api";

/**
 * The outcome and by-station sections of a result, as the candidate sees them.
 *
 * Shared by the candidate's own page and the staff preview, so the two cannot drift.
 * It draws whatever it is given: whether a result may be shown at all is the caller's
 * call (the candidate's page refuses an unreleased one; the preview exists to show it).
 */
export function ResultView({ result, actions }: { result: TraineeResult; actions?: ReactNode }) {
  return (
    <>
      <B2CHero
        eyebrow="Outcome"
        title={
          result.assessment_score != null
            ? `${outcomeLabel(result.assessment_outcome)}, ${result.assessment_score.toFixed(1)} / 100`
            : outcomeLabel(result.assessment_outcome)
        }
        action={actions}
      >
        {result.rationale ? <span className="whitespace-pre-wrap">{result.rationale}</span> : null}
      </B2CHero>
      {result.stations && result.stations.length > 0 ? (
        <B2CGroupedSection eyebrow="By station">
          {result.stations.map((station) => (
            <B2CGroupedRow
              key={station.slot_id}
              title={station.station_title ?? "Station"}
              trailing={<Badge tone="neutral">{stationScoreLabel(station)}</Badge>}
            />
          ))}
        </B2CGroupedSection>
      ) : null}
    </>
  );
}

/**
 * The outcome in words.
 *
 * A result that exists with no outcome on it is possible — a decision can be
 * released as withheld — so "recorded" is said rather than an empty heading.
 */
function outcomeLabel(outcome: string | null | undefined): string {
  if (!outcome) return "Recorded";
  return outcome.replace(/_/g, " ").replace(/^\w/, (letter) => letter.toUpperCase());
}
