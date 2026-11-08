"use client";

import type { ReactNode } from "react";
import { boardChip } from "@/foundation/ui/boardKit";
import { useSurface } from "@/capabilities";
import type { TraineeResult } from "@/domains/assess/trainee/api";
import { resultHero, resultRows } from "@/domains/assess/trainee/hireCopy";
import { TraineeHero, TraineeList, TraineeRowLink } from "@/domains/assess/trainee/traineeBoard";

/**
 * An employer's candidate's released result (HireCandidateResult): "Pass · 4 of 5 stations", the one action
 * ("I have read this", passed in by the page), and a row per station into its feedback. It draws only the fields
 * `/me/results/{id}` returns, which has no hiring decision, and it offers no practice.
 */
export function HireResult({ result, org, action }: { result: TraineeResult; org: string; action: ReactNode }) {
  const { hrefFor } = useSurface();
  const hero = resultHero(result, org);
  const rows = resultRows(result);

  return (
    <>
      <TraineeHero eyebrow="Your result" title={hero.title} size="xl" action={action}>
        {hero.meta}
      </TraineeHero>
      {rows.length > 0 ? (
        <TraineeList title="Stations" untitled>
          {rows.map((row) => (
            <TraineeRowLink key={row.slotId} href={hrefFor(`/trainee/reviews/${row.slotId}`)} title={row.label}>
              <span className={boardChip(row.ok ? "ok" : "live")}>{row.chip}</span>
              <span className="w-[140px] text-assess-meta text-osce-ink-500">See feedback</span>
            </TraineeRowLink>
          ))}
        </TraineeList>
      ) : null}
    </>
  );
}
