import type { RagRow } from "@/foundation/charts/RagCompositionBars";
/* From the theme module rather than the charts barrel: this file is data,
 * imported by a test that does not render, and the barrel pulls in Recharts. */
import { chartColors } from "@/foundation/charts/chartTheme";
import {
  bandLegend,
  formatNumber,
  readDisplay,
  toneVariant,
  type Aggregate,
  type Display,
  type Rating,
} from "@/capabilities/feedback/rubric";
import type { Performance, PerformanceDomain } from "@/domains/train/api";

/**
 * The learner dashboard, read off the rubric's display.
 *
 * `/me/performance` sends the marked work *and* the display block of the
 * exam's rubric: how a domain is summed, the pass lines, the chart titles. So
 * the dashboard is one screen for every exam, and nothing here knows an exam
 * code. What used to be a table of four exams (`examConfig`) is now whatever
 * the author wrote; a fifth exam gets a correct dashboard with no release.
 *
 * Kept free of React so a test can assert the literal words and numbers a
 * person sees.
 */

/** A chart's scale: its maximum, pass line, axis ticks and how a value is written. */
export interface ChartScale {
  subtitle: string;
  maxScore: number;
  threshold?: number;
  thresholdLabel?: string;
  ticks: number[];
  format: (value: number) => string;
  /** Axis labels: a bare number, or "40%" for a share. */
  formatTick: (value: number) => string;
}

export interface SummaryCard {
  metric: "pass_rate" | "fail_rate";
  title: string;
  value: string;
  description: string;
  tone: "primary" | "default";
}

/** A domain's bar, for the threshold chart. */
export interface DomainBar {
  name: string;
  score: number;
  color: string;
}

export type DomainChart =
  /** A scale counted per domain (SCA): one stacked bar of best / middle / worst per domain. */
  | { kind: "counts"; subtitle: string; rows: RagRow[] }
  /** Anything summed or averaged: one bar per domain against the domain pass line. */
  | ({ kind: "bars"; bars: DomainBar[] } & ChartScale);

export interface DashboardView {
  title: string;
  /**
   * The total is a share of the best grade rather than a score with a pass
   * line, so the screen leads with the competency mix (hero, weekly column,
   * what to work on) instead of pass and fail rates.
   */
  counted: boolean;
  summaryCards: SummaryCard[];
  /** The mix of best / middle / worst grades across every domain, for the hero. */
  hero: { competent: number; developing: number; development: number };
  domainChart: DomainChart;
  trend: ChartScale & { points: Array<{ date: string; score: number }> };
  /** How often each domain landed in each tone, one row per domain. */
  composition: RagRow[];
  /** Named bands for a station total, e.g. "0–17 Poor". */
  bands: string[];
  /** Said out loud when attempts were marked under different rubric versions. */
  versionNotice: string | null;
  /** The weakest domains, for "What to work on". */
  insights: Array<{ text: string; domain: string }>;
  display: Display | null;
}

/* ---------- helpers ---------- */

const PALETTE = [chartColors.primary, chartColors.green, chartColors.amber, chartColors.indigo, chartColors.slate];

/** Five even ticks from 0 to the maximum, with the pass line added if it falls between them. */
export function ticksFor(maxScore: number, threshold?: number): number[] {
  const even = [0, 1, 2, 3, 4].map((step) => Math.round(((maxScore * step) / 4) * 100) / 100);
  const all = threshold === undefined ? even : [...even, threshold];
  return [...new Set(all)].sort((left, right) => left - right);
}

/** A value in its aggregate's units: "1.2 / 4" for a sum, "67%" for a share. */
function formatterFor(aggregate: Aggregate, max: number | null): (value: number) => string {
  if (aggregate === "sum" || aggregate === "mean") {
    return (value) => (max === null ? formatNumber(value) : `${formatNumber(value)} / ${formatNumber(max)}`);
  }
  return (value) => `${Math.round(value)}%`;
}

function tickFormatterFor(aggregate: Aggregate): (value: number) => string {
  return aggregate === "sum" || aggregate === "mean" ? (value) => formatNumber(value) : (value) => `${Math.round(value)}%`;
}

function isShare(aggregate: Aggregate | undefined): boolean {
  return aggregate === "ragShare" || aggregate === "ragCounts";
}

/** Counts per scale value, folded into the three bands the RAG charts draw: best, middle, worst. */
function foldCounts(rating: Rating | null, counts: Record<string, number> | undefined): Omit<RagRow, "name"> {
  const scale = rating?.scale ?? [];
  const folded = { "Requires Development": 0, "Developing Competency": 0, Competent: 0 };
  scale.forEach((value, index) => {
    const count = counts?.[value] ?? 0;
    if (index === 0) folded.Competent += count;
    else if (index === scale.length - 1) folded["Requires Development"] += count;
    else folded["Developing Competency"] += count;
  });
  return folded;
}

/** Tone counts (`{poor: 1, good: 2}`) folded the same way, by the badge colour each tone reads as. */
function foldTones(tones: Record<string, number> | undefined): Omit<RagRow, "name"> {
  const folded = { "Requires Development": 0, "Developing Competency": 0, Competent: 0 };
  for (const [tone, count] of Object.entries(tones ?? {})) {
    const variant = toneVariant(tone);
    if (variant === "success") folded.Competent += count;
    else if (variant === "danger") folded["Requires Development"] += count;
    else folded["Developing Competency"] += count;
  }
  return folded;
}

function percentOf(part: number, whole: number): number {
  return whole === 0 ? 0 : Math.round((100 * part) / whole);
}

/** Up to three domains to practise next, weakest first, on the 0–100 score every domain carries. */
export function weakestDomains(domains: readonly PerformanceDomain[]): Array<{ text: string; domain: string }> {
  return [...domains]
    .filter((domain) => Number.isFinite(domain.score) && domain.label.trim() !== "")
    .sort((left, right) => left.score - right.score || left.label.localeCompare(right.label))
    .slice(0, 3)
    .map((domain) => ({ text: domain.label, domain: `${Math.round(domain.score)}%` }));
}

/* ---------- the view ---------- */

export function dashboardView(performance: Performance | null): DashboardView {
  const display = readDisplay(performance?.display ?? null);
  const labels = display?.labels ?? {};
  const rating = performance?.rating ?? null;
  const domains = performance?.domains ?? [];
  const summary = performance?.summary ?? null;
  const counted = isShare(display?.total.aggregate);

  // Pass and fail rates only mean something where the rubric sets a pass line;
  // the API sends null rates otherwise, and an empty card would say "0%".
  const summaryCards: SummaryCard[] =
    summary && summary.pass_rate !== null && summary.pass_rate !== undefined
      ? [
          {
            metric: "pass_rate",
            title: "Strong Performance",
            value: `${Math.round((summary.pass_rate ?? 0) * 100)}%`,
            description: labels.passLabel
              ? `Stations at or above the pass line: ${labels.passLabel}`
              : "Stations where you met the pass line",
            tone: "primary",
          },
          {
            metric: "fail_rate",
            title: "Growth Opportunities",
            value: `${Math.round((summary.fail_rate ?? 0) * 100)}%`,
            description: "Stations with room for improvement and development",
            tone: "default",
          },
        ]
      : [];

  const summed = domains.map((domain) => foldCounts(rating, domain.counts ?? undefined));
  const competent = summed.reduce((total, row) => total + row.Competent, 0);
  const developing = summed.reduce((total, row) => total + row["Developing Competency"], 0);
  const development = summed.reduce((total, row) => total + row["Requires Development"], 0);
  const marks = competent + developing + development;

  const domainAggregate = display?.domain.aggregate ?? "percentAchieved";
  // A share aggregate is out of 100 already; a sum or mean is in the rating's own units.
  const domainMax = isShare(domainAggregate) || domainAggregate === "percentAchieved" ? 100 : (display?.domain.max ?? 100);
  const domainThreshold = display?.domain.passAtLeast ?? undefined;
  const domainChart: DomainChart =
    domainAggregate === "ragCounts"
      ? {
          kind: "counts",
          subtitle: labels.domainSubtitle ?? "Grades by domain",
          rows: domains.map((domain, index) => ({ name: domain.label, ...(summed[index] ?? foldCounts(null, undefined)) })),
        }
      : {
          kind: "bars",
          subtitle: labels.domainSubtitle ?? "Score by domain",
          maxScore: domainMax,
          threshold: domainThreshold,
          thresholdLabel: domainThreshold !== undefined ? labels.domainPassLabel : undefined,
          ticks: ticksFor(domainMax, domainThreshold),
          format: formatterFor(domainAggregate, domainMax),
          formatTick: tickFormatterFor(domainAggregate),
          bars: domains.map((domain, index) => ({
            name: domain.label,
            score: domain.value ?? domain.score,
            color: PALETTE[index % PALETTE.length] ?? chartColors.muted,
          })),
        };

  // A counted exam's trend is the share at the best grade, 0 to 100 with no
  // pass line; every other exam's is the station total against its own.
  const totalAggregate = display?.total.aggregate ?? "percentAchieved";
  const trendMax = counted || totalAggregate === "percentAchieved" ? 100 : (display?.total.max ?? 100);
  const trendThreshold = counted ? undefined : (display?.total.passAtLeast ?? undefined);
  const trend = {
    subtitle: labels.trendSubtitle ?? "Score over time",
    maxScore: trendMax,
    threshold: trendThreshold,
    thresholdLabel: trendThreshold !== undefined ? labels.passLabel : undefined,
    ticks: ticksFor(trendMax, trendThreshold),
    format: formatterFor(counted ? "ragShare" : totalAggregate, trendMax),
    formatTick: tickFormatterFor(counted ? "ragShare" : totalAggregate),
    points: (performance?.trend ?? []).map((point) => ({
      date: point.date,
      score: counted ? point.score : (point.total ?? point.score),
    })),
  };

  const versions = performance?.rubric_versions ?? 1;
  return {
    title: labels.title ?? "Dashboard",
    counted,
    summaryCards,
    hero: {
      competent: percentOf(competent, marks),
      developing: percentOf(developing, marks),
      development: percentOf(development, marks),
    },
    domainChart,
    trend,
    composition: (performance?.composition ?? []).map((row) => ({ name: row.label, ...foldTones(row.tones) })),
    bands: bandLegend(display),
    versionNotice: performance?.mixed_versions ? `Scored under ${versions} rubric versions` : null,
    insights: weakestDomains(domains),
    display,
  };
}

/**
 * The status chip on a recent attempt. A debrief is never marked, so "has a result" cannot say it
 * is over: once its transcript is in it is finished, not "In progress" for ever (staging, 2026-10-03).
 */
export function recentAttemptStatus(attempt: { kind: string; status: string; has_result: boolean }): string {
  if (attempt.has_result) return "Marked";
  if (attempt.status === "created") return "Not started";
  if (attempt.status === "running") return "In progress";
  if (attempt.status === "failed") return "Not completed";
  return attempt.kind === "debrief" ? "Finished" : "Marking";
}
