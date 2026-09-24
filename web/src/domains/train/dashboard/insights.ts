import type { InsightItem } from "@/domains/train/dashboard/InsightsList";
import { formatScore, type ExamChartScale } from "@/domains/train/dashboard/examConfig";

export interface ScoredDomain {
  label: string;
  score: number;
}

/**
 * Up to three domains to practise next, weakest first.
 *
 * Drawn from the scores `/me/performance` already returned. Nothing here
 * writes clinical advice: the line is the domain's own name and its mark.
 */
export function weakestInsights(
  domains: readonly ScoredDomain[] | null | undefined,
  scale: ExamChartScale,
): InsightItem[] {
  return [...(domains ?? [])]
    .filter((domain) => Number.isFinite(domain.score) && domain.label.trim() !== "")
    .sort((a, b) => a.score - b.score || a.label.localeCompare(b.label))
    .slice(0, 3)
    .map((domain) => ({
      text: domain.label,
      domain: formatScore(scale, domain.score),
    }));
}
