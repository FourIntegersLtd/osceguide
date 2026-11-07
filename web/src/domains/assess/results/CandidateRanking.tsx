"use client";

import { boardButtonSmall, boardCard, boardChip, boardRow } from "@/foundation/ui/boardKit";
import { b2bTokens as t } from "@/foundation/ui";
import type { CandidateReport } from "@/domains/assess/results/api";
import { rankCandidates } from "@/domains/assess/results/ranking";
import { TONE_CHIP } from "@/domains/assess/results/CandidateCard";
import { candidateName, formatScore, recruitmentLabel, recruitmentTone } from "@/domains/assess/results/support";
import { useAssessWords } from "@/domains/assess/useAssessWords";

/**
 * Candidates side by side, best first, so a hiring decision is made with the others in view.
 * From the sitting report already on screen; each row opens that candidate's decision below.
 */
export function CandidateRanking({
  candidates,
  openId,
  onOpen,
}: {
  candidates: CandidateReport[];
  openId: string | null;
  onOpen: (userId: string) => void;
}) {
  const w = useAssessWords();
  const ranked = rankCandidates(candidates);
  if (ranked.length < 2) return null;
  return (
    <section aria-label="Ranking" className={`${boardCard} overflow-hidden`}>
      <div className={`${boardRow} border-t-0`}>
        <div>
          <div className={t.assessEyebrow}>Ranking</div>
          <div className={t.assessMeta}>{`Best first, by score and then stations passed. Open ${w.trainee === "candidate" ? "a candidate" : `a ${w.trainee}`} to decide.`}</div>
        </div>
      </div>
      {ranked.map(({ rank, candidate }) => {
        const hiring = candidate.decision?.recruitment_outcome;
        const name = candidateName(candidate);
        return (
          <div key={candidate.user_id} className={boardRow}>
            <span className="w-8 font-semibold">{rank ?? "-"}</span>
            <span className="flex-[1_1_180px] font-medium">{name}</span>
            <span className="w-[70px]">{formatScore(candidate.score, "No score")}</span>
            <span className={`flex-[1_1_140px] ${t.assessMeta}`}>{`${candidate.stations_passed} of ${candidate.stations_marked} stations passed`}</span>
            <span className="w-[110px]">
              {hiring && hiring !== "pending" ? (
                <span className={boardChip(TONE_CHIP[recruitmentTone(hiring)])}>{recruitmentLabel(hiring)}</span>
              ) : (
                <span className={t.assessMeta}>To decide</span>
              )}
            </span>
            <button
              type="button"
              className={boardButtonSmall}
              aria-expanded={openId === candidate.user_id}
              aria-label={`Decide ${name}`}
              onClick={() => onOpen(candidate.user_id)}
            >
              Decide
            </button>
          </div>
        );
      })}
    </section>
  );
}
