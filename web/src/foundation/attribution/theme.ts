import { chartColors } from "@/foundation/charts/chartTheme";

/**
 * The partner dashboard's warm palette, kept out of the shared chart theme so
 * a consumer's blue RAG bars and a partner's amber funnel cannot bleed into
 * each other. Every hue is a `chartColors` token or an explicit warm step.
 */
const orange = "#ea580c";
const orangeDeep = "#c2410c";

export const funnelStepColors = {
  landing: chartColors.amber,
  signup: orange,
  purchase: chartColors.green,
} as const;

export const seriesColors = {
  linkVisits: orange,
  signups: chartColors.amber,
  revenue: chartColors.green,
  fees: orangeDeep,
  spend: chartColors.amber,
  marginPositive: orange,
  marginNegative: chartColors.red,
} as const;

const examColors: Record<string, string> = {
  sca: chartColors.amber,
  plab: orange,
  ortho: chartColors.green,
};

const fallbackCycle = [chartColors.amber, orange, orangeDeep, chartColors.green];

export function examColor(exam: string, index: number): string {
  return examColors[exam.toLowerCase()] ?? fallbackCycle[index % fallbackCycle.length] ?? orange;
}
