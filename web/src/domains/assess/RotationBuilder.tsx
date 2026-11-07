"use client";

import { useRef, useState } from "react";
import { b2bTokens as t, cn } from "@/foundation/ui";
import { plural } from "@/foundation/format";
import { smallButton } from "@/domains/assess/SittingFields";
import { assessorTally, proposeRotations, reconcileRotations, tallyText } from "@/domains/assess/rotations";
import type { ScheduleDraft } from "@/domains/assess/scheduleSitting";
import { useAssessWords } from "@/domains/assess/useAssessWords";

/**
 * Tick who assesses and the candidates are dealt between them: one rotation (circuit) each, an
 * even load. What it proposes is written into the same per-candidate choices the list under it
 * edits, so the person can change any of them before anything is saved.
 */
export function RotationBuilder({
  draft,
  patch,
  leads,
}: {
  draft: ScheduleDraft;
  patch: (change: Partial<ScheduleDraft>) => void;
  leads: { value: string; label: string }[];
}) {
  const w = useAssessWords();
  const [pool, setPool] = useState<string[]>(() => leads.map((l) => l.value).filter((id) => Object.values(draft.supervisorByCandidate).includes(id)));
  // What was last dealt, so a choice the person made by hand in the list below is known and kept.
  const lastDealt = useRef<Record<string, string>>({});
  const apply = (next: string[], dealt: Record<string, string>) => {
    setPool(next);
    lastDealt.current = dealt;
    patch({ supervisorByCandidate: dealt });
  };
  const toggle = (id: string) => {
    const next = leads.map((l) => l.value).filter((value) => (value === id ? !pool.includes(id) : pool.includes(value)));
    apply(next, reconcileRotations(draft.candidateIds, draft.supervisorByCandidate, lastDealt.current, next));
  };
  const tally = assessorTally(
    draft.candidateIds,
    draft.supervisorByCandidate,
    Object.fromEntries(leads.map((l) => [l.value, l.label])),
  );
  const count = draft.candidateIds.length;

  return (
    <fieldset className={cn(t.assessCard, "flex flex-col gap-3 p-6")}>
      <legend className="sr-only">{`Build the ${w.circuits}`}</legend>
      <div>
        <p className="font-medium">{`Build the ${w.circuits}`}</p>
        <p className={t.assessMeta}>
          {`Choose who marks. We deal the ${plural(count, w.trainee, w.trainees)} between them, one ${w.circuit} each. Change any ${w.circuit} below.`}
        </p>
      </div>
      <div className="flex flex-wrap gap-x-5 gap-y-2">
        {leads.map((lead) => (
          <label key={lead.value} className="inline-flex min-h-11 items-center gap-2 text-assess-label">
            <input type="checkbox" checked={pool.includes(lead.value)} onChange={() => toggle(lead.value)} />
            {lead.label}
          </label>
        ))}
      </div>
      {pool.length > 0 ? (
        <div className="flex flex-wrap items-center gap-3">
          <p className={t.assessMeta} role="status">
            {tallyText(tally)}
          </p>
          <button type="button" className={smallButton} onClick={() => apply(pool, proposeRotations(draft.candidateIds, pool))}>
            Deal again
          </button>
        </div>
      ) : null}
    </fieldset>
  );
}
