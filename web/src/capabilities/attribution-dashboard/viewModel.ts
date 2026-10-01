import type { components } from "@/foundation/platform-client";
import { funnelStepColors, examColor, seriesColors } from "@/capabilities/attribution-dashboard/theme";
import type { DashboardCopy } from "@/capabilities/attribution-dashboard/copy";
import { formatMoney } from "@/foundation/format";
import type { AttributionMode, RevenueTimeBucket } from "@/capabilities/attribution-dashboard/types";

type S = components["schemas"];

/** The bucket a chart's points are grouped by, chosen from the range's length. */
export function bucketForRange(fromDate: string, toDate: string): RevenueTimeBucket {
  const days =
    (Date.parse(`${toDate}T00:00:00Z`) - Date.parse(`${fromDate}T00:00:00Z`)) / 86_400_000 + 1;
  if (days <= 62) return "day";
  if (days <= 200) return "week";
  return "month";
}

/** The API returns the bucket as a string; anything unknown reads as daily. */
export function asBucket(value: string): RevenueTimeBucket {
  return value === "week" || value === "month" ? value : "day";
}

export interface FunnelCounts {
  landing: number | null;
  signup: number | null;
  purchase: number | null;
}

/** The three counted steps, preferring the funnel's own numbers over the summary's. */
export function funnelCounts(
  funnel: S["FunnelRead"] | null,
  fallback: { visits: number; signups: number; paid: number },
): FunnelCounts {
  const step = (name: string): number | null | undefined =>
    funnel?.steps?.find((candidate) => candidate.step === name)?.count;
  return {
    landing: step("landing") === undefined ? fallback.visits : (step("landing") ?? null),
    signup: step("signup") === undefined ? fallback.signups : (step("signup") ?? null),
    purchase: step("purchase") === undefined ? fallback.paid : (step("purchase") ?? null),
  };
}

export interface FunnelStepView {
  key: "landing" | "signup" | "purchase";
  label: string;
  count: number | null;
  /** Share of visits, rounded; null when there were no visits or no count. */
  percentOfVisits: number | null;
  color: string;
}

const FUNNEL_LABELS = { landing: "Visited", signup: "Signed up", purchase: "Paid" } as const;

export function funnelStepViews(counts: FunnelCounts): FunnelStepView[] {
  return (["landing", "signup", "purchase"] as const).map((key) => {
    const count = counts[key];
    const percent =
      count === null || !counts.landing ? null : Math.round((count / counts.landing) * 100);
    return {
      key,
      label: FUNNEL_LABELS[key],
      count,
      percentOfVisits: percent,
      color: funnelStepColors[key],
    };
  });
}

export interface DonutSlice {
  name: string;
  value: number;
  color: string;
}

/** Visited-only, signed-up-only and paid, so the ring sums to the visits. Empty slices are dropped. */
export function funnelDonutSlices(counts: FunnelCounts): DonutSlice[] {
  const landing = counts.landing ?? 0;
  const signup = counts.signup ?? 0;
  const purchase = counts.purchase ?? 0;
  return [
    { name: "Visited", value: Math.max(landing - signup, 0), color: funnelStepColors.landing },
    { name: "Signed up", value: Math.max(signup - purchase, 0), color: funnelStepColors.signup },
    { name: "Paid", value: purchase, color: funnelStepColors.purchase },
  ].filter((slice) => slice.value > 0);
}

/** The donut's centre: what share of visits signed up. */
export function signedUpPercent(counts: FunnelCounts): number {
  const landing = counts.landing ?? 0;
  if (landing <= 0) return 0;
  return Math.round(((counts.signup ?? 0) / landing) * 100);
}

export type MetricTone = "blue" | "amber" | "orange" | "emerald";

export type HeroIcon =
  | "visits"
  | "unique"
  | "signups"
  | "paid"
  | "revenue"
  | "spend"
  | "margin"
  | "perSignup"
  | "fee";

export interface HeroStat {
  key: HeroIcon;
  label: string;
  value: string;
  tone: MetricTone;
  tooltip: string;
}

/** What the hero card needs. A partner's never carries revenue, margin or spend. */
export interface HeroFigures {
  visits: number;
  unique: number;
  signups: number;
  paid: number;
  feePence: number;
  internal?: {
    revenuePence: number;
    spend: {
      estimatedSpendPence: number;
      netMarginPence: number;
      costPerAcquisitionPence: number | null;
    } | null;
  };
}

export function internalHeroFigures(summary: S["DashboardSummaryRead"]): HeroFigures {
  return {
    visits: summary.raw_arrival_count,
    unique: summary.unique_arrival_count,
    signups: summary.acquired_user_count,
    paid: summary.revenue.paying_user_count,
    feePence: 0,
    internal: {
      revenuePence: summary.revenue.gross_revenue_pence,
      spend: summary.spend
        ? {
            estimatedSpendPence: summary.spend.estimated_spend_pence,
            netMarginPence: summary.spend.net_margin_pence,
            costPerAcquisitionPence: summary.spend.cost_per_acquisition_pence ?? null,
          }
        : null,
    },
  };
}

export function partnerHeroFigures(summary: S["PartnerDashboardSummaryRead"]): HeroFigures {
  return {
    visits: summary.raw_arrival_count,
    unique: summary.unique_arrival_count,
    signups: summary.acquired_user_count,
    paid: summary.paying_user_count,
    feePence: summary.fee.estimated_spend_pence,
  };
}

export function heroHasData(figures: HeroFigures): boolean {
  return figures.visits > 0 || figures.signups > 0 || figures.paid > 0 || figures.feePence > 0;
}

/** The cards in the hero, in the order the legacy dashboard showed them. */
export function heroStats(
  mode: AttributionMode,
  figures: HeroFigures,
  copy: DashboardCopy["hero"],
): HeroStat[] {
  const { metrics, spend: spendCopy } = copy;
  if (mode === "partner") {
    const people = figures.unique;
    return [
      {
        key: "visits",
        label: metrics.linkVisits.label,
        value: String(figures.visits),
        tone: "orange",
        tooltip:
          people > 0
            ? `${metrics.linkVisits.tooltip} ${people} unique ${people === 1 ? "person" : "people"}.`
            : metrics.linkVisits.tooltip,
      },
      {
        key: "signups",
        label: metrics.signups.label,
        value: String(figures.signups),
        tone: "amber",
        tooltip: metrics.signups.tooltip,
      },
      {
        key: "fee",
        label: metrics.estimatedFee.label,
        value: formatMoney(figures.feePence),
        tone: "orange",
        tooltip: metrics.estimatedFee.tooltip,
      },
    ];
  }
  const stats: HeroStat[] = [
    { key: "visits", label: metrics.linkVisits.label, value: String(figures.visits), tone: "orange", tooltip: metrics.linkVisits.tooltip },
    { key: "unique", label: metrics.uniquePeople.label, value: String(figures.unique), tone: "amber", tooltip: metrics.uniquePeople.tooltip },
    { key: "signups", label: metrics.signups.label, value: String(figures.signups), tone: "orange", tooltip: metrics.signups.tooltip },
    { key: "paid", label: metrics.paid.label, value: String(figures.paid), tone: "emerald", tooltip: metrics.paid.tooltip },
    {
      key: "revenue",
      label: metrics.revenue.label,
      value: formatMoney(figures.internal?.revenuePence ?? 0),
      tone: "amber",
      tooltip: metrics.revenue.tooltip,
    },
  ];
  const spend = figures.internal?.spend;
  if (spend) {
    stats.push(
      {
        key: "spend",
        label: spendCopy.estimatedSpend.label,
        value: formatMoney(spend.estimatedSpendPence),
        tone: "amber",
        tooltip: spendCopy.estimatedSpend.tooltip,
      },
      {
        key: "margin",
        label: spendCopy.moneyLeftOver.label,
        value: formatMoney(spend.netMarginPence),
        tone: spend.netMarginPence >= 0 ? "emerald" : "amber",
        tooltip: spendCopy.moneyLeftOver.tooltip,
      },
      {
        key: "perSignup",
        label: spendCopy.spendPerSignup.label,
        value:
          spend.costPerAcquisitionPence === null ? "-" : formatMoney(spend.costPerAcquisitionPence),
        tone: "orange",
        tooltip: spendCopy.spendPerSignup.tooltip,
      },
    );
  }
  return stats;
}

/** Definitions a partner may read: the ones flagged internal-only are dropped. */
export function visibleDefinitions(
  mode: AttributionMode,
  definitions: DashboardCopy["methodology"]["definitions"],
): DashboardCopy["methodology"]["definitions"] {
  return mode === "partner" ? definitions.filter((entry) => !entry.internalOnly) : definitions;
}

/** `gold_monthly` becomes `Gold Monthly`. */
export function planLabel(planType: string): string {
  return planType
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export interface Bar {
  label: string;
  value: number;
  color: string;
}

/** Spend, money in and what is left, as three bars. Left-over turns red when negative. */
export function costVsRevenueBars(spend: S["PartnerSpendRead"]): Bar[] {
  return [
    { label: "Est. BMJ spend", value: spend.estimated_spend_pence, color: seriesColors.spend },
    { label: "Money in", value: spend.gross_revenue_pence, color: seriesColors.revenue },
    {
      label: "Money left over",
      value: spend.net_margin_pence,
      color: spend.net_margin_pence >= 0 ? seriesColors.marginPositive : seriesColors.marginNegative,
    },
  ];
}

export function hasSpendOrRevenue(spend: S["PartnerSpendRead"]): boolean {
  return spend.estimated_spend_pence !== 0 || spend.gross_revenue_pence !== 0;
}

export interface ExamShareRow {
  exam: string;
  visits: number;
  signups: number;
  /** Share of all visits, rounded. */
  sharePercent: number;
  color: string;
}

/** Exams by visits, largest first, each with its share of the total. */
export function examShareRows(rows: S["PartnerBreakdownRow"][]): ExamShareRow[] {
  const total = rows.reduce((sum, row) => sum + row.visit_count, 0);
  return [...rows]
    .sort((left, right) => right.visit_count - left.visit_count)
    .map((row, index) => ({
      exam: row.dimension.toUpperCase(),
      visits: row.visit_count,
      signups: row.signup_count,
      sharePercent: total > 0 ? Math.round((row.visit_count / total) * 100) : 0,
      color: examColor(row.dimension, index),
    }));
}

export interface SeriesPoint {
  period: string;
  value: number;
  /** A second figure the tooltip quotes (a fee's visits). */
  extra?: number;
}

export function countPoints(report: S["CountOverTimeReport"]): SeriesPoint[] {
  return report.points.map((point) => ({ period: point.period, value: point.count }));
}

export function feePoints(report: S["FeeOverTimeReport"]): SeriesPoint[] {
  return report.points.map((point) => ({
    period: point.period,
    value: point.estimated_fee_pence,
    extra: point.visit_count,
  }));
}

export function revenuePoints(report: S["RevenueOverTimeReport"]): SeriesPoint[] {
  return report.points.map((point) => ({
    period: point.period,
    value: point.gross_revenue_pence,
    extra: point.payment_count,
  }));
}

/** No points at all, or points that are all zero. */
export function seriesIsFlat(points: SeriesPoint[]): boolean {
  return points.every((point) => point.value === 0);
}

/** The API names an empty campaign "unknown"; the dashboard has always shown a dash. */
export function campaignLabel(value: string | null | undefined): string {
  return !value || value === "unknown" ? "-" : value;
}

/** The partner's display name in prose ("bmj" is "BMJ On Exam"). */
export function partnerDisplayName(slug: string | null | undefined): string {
  if (!slug) return "our partner";
  const key = slug.toLowerCase();
  return key === "bmj" ? "BMJ On Exam" : key.replace(/[-_]+/g, " ").toUpperCase();
}
