/*
 * The product's charts, brought across with the dashboards that use them.
 *
 * Twelve components and one theme, all Recharts. Kept together as their own
 * foundation module rather than scattered into whichever screen first needed
 * one: a RAG bar has to mean the same thing on a consumer dashboard and an
 * institution's cohort report, and `chartTheme` is what makes that true.
 */
export { default as CategoryVolumeChart } from "@/foundation/charts/CategoryVolumeChart";
export { default as CategoryVolumeList } from "@/foundation/charts/CategoryVolumeList";
export { default as ChartCard } from "@/foundation/charts/ChartCard";
export { default as ChartEmptyState } from "@/foundation/charts/ChartEmptyState";
export {
  default as OutcomeDonut,
  defaultRagSlices,
  defaultPassFailSlices,
  type OutcomeSlice,
} from "@/foundation/charts/OutcomeDonut";
export { default as RagCompositionBars, type RagRow } from "@/foundation/charts/RagCompositionBars";
export { default as RagMixList } from "@/foundation/charts/RagMixList";
export { default as RagStackBars } from "@/foundation/charts/RagStackBars";
export {
  default as ScoreTrendChart,
  type ScoreTrendPoint,
} from "@/foundation/charts/ScoreTrendChart";
export { default as SkillBeforeAfterChart } from "@/foundation/charts/SkillBeforeAfterChart";
export { default as SkillSlopeChart } from "@/foundation/charts/SkillSlopeChart";
export {
  default as ThresholdBars,
  type ThresholdBarDatum,
} from "@/foundation/charts/ThresholdBars";
export * from "@/foundation/charts/chartTheme";
