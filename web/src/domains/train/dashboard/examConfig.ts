import { b2cDesignTokens } from "@/foundation/ui/designTokens";
/* From the theme module rather than the charts barrel: this file is data,
 * imported by a test that does not render, and the barrel pulls in twelve
 * Recharts components to get one palette. */
import { chartColors } from "@/foundation/charts/chartTheme";

/**
 * The four exam dashboards, as data.
 *
 * The retiring client had one screen per exam — `sca/dashboard`,
 * `plab/dashboard`, `casc/dashboard`, `ortho/dashboard` — 8.4k lines whose
 * differences were domain names, bar colours, a maximum score, a pass
 * threshold and the wording around them. Three of them were the same file
 * three times over, and a fix to one (the chart's empty state, twice) reached
 * only the copy the author happened to open.
 *
 * So the screen is one component and an exam is a row in this table. SCA is
 * genuinely richer rather than differently worded, and says so here with
 * `sections`: the competency hero, the weekly trend and the insights list are
 * switched on by configuration, not by a second implementation.
 */

export interface ExamSummaryCard {
  /** Which rate from `/me/performance` the card shows. */
  metric: "pass_rate" | "fail_rate" | "critical_rate";
  title: string;
  description: string;
  /** The first card is the filled accent one, as it is today. */
  tone: "primary" | "default";
  icon: "pass" | "fail" | "critical";
}

export interface ExamChartScale {
  subtitle: string;
  maxScore: number;
  /** Omitted where the exam has no published per-domain minimum (SCA). */
  threshold?: number;
  thresholdLabel?: string;
  ticks: number[];
  /** Scores arrive as a 0–1 proportion and read as percentages. */
  percent?: boolean;
  /** Decimal places on the value in a tooltip. */
  decimals?: number;
  /** Rendered after the value, e.g. `/ 12`. */
  unit?: string;
}

export interface ExamDomainChart extends ExamChartScale {
  layout: "horizontal" | "vertical";
  yAxisWidth?: number;
  height?: number;
  /** Fixed colour per domain label, as each old dashboard hard-coded. */
  colors?: Record<string, string>;
  /** Fallback ramp where the domains are not known ahead of time. */
  palette?: string[];
  /**
   * Ortho only: its domain labels are `"<station type> - <domain>"`, and the
   * old screen offered an average per station type with a drill-down into one
   * type's domains. The grouping lives here because it is the exam's rubric
   * that is shaped that way, not the screen.
   */
  groupByStationType?: boolean;
}

export interface ExamSections {
  /** SCA's competency doughnut, from the pass/critical/fail split. */
  hero: boolean;
  /** SCA's eight-week rolling bar column. */
  weeklyTrend: boolean;
  /** SCA's "What to work on" list. */
  insights: boolean;
  /** SCA's "Ready for your first station?" prompt, before any attempt. */
  firstStation: boolean;
}

export interface ExamConfig {
  code: string;
  /** How the exam is named in a sentence. */
  label: string;
  /** "exam" for the three exams, "interview" for Ortho ST3. */
  eventNoun: string;
  title: string;
  /** `null` where the exam's header carries no welcome line (SCA). */
  subtitle: string | null;
  summaryTitle: string;
  summaryCards: ExamSummaryCard[];
  domains: ExamDomainChart;
  trend: ExamChartScale;
  sections: ExamSections;
}

const STRONG: ExamSummaryCard = {
  metric: "pass_rate",
  title: "Strong Performance",
  description: "Stations where you demonstrated confident competency",
  tone: "primary",
  icon: "pass",
};

const GROWTH: ExamSummaryCard = {
  metric: "fail_rate",
  title: "Growth Opportunities",
  description: "Stations with room for improvement and development",
  tone: "default",
  icon: "fail",
};

const NO_EXTRA_SECTIONS: ExamSections = {
  hero: false,
  weeklyTrend: false,
  insights: false,
  firstStation: false,
};

const PLAB: ExamConfig = {
  code: "plab",
  label: "PLAB",
  eventNoun: "exam",
  title: "Dashboard",
  subtitle: "Here is your PLAB performance overview.",
  summaryTitle: "Performance overview",
  summaryCards: [STRONG, GROWTH],
  domains: {
    subtitle: "Average score out of 4",
    maxScore: 4,
    threshold: 2,
    thresholdLabel: "Min threshold",
    ticks: [0, 1, 2, 3, 4],
    decimals: 2,
    unit: "/ 4",
    layout: "horizontal",
    yAxisWidth: 150,
    colors: {
      "Data Gathering": "#4ade80",
      "Clinical Management": b2cDesignTokens.accent.DEFAULT,
      "Interpersonal Skills": "#f97316",
    },
  },
  trend: {
    subtitle: "Station score over time",
    maxScore: 12,
    threshold: 7,
    thresholdLabel: "Pass (7/12)",
    ticks: [0, 3, 6, 9, 12],
    decimals: 1,
    unit: "/ 12",
  },
  sections: NO_EXTRA_SECTIONS,
};

const CASC: ExamConfig = {
  code: "casc",
  label: "CASC",
  eventNoun: "exam",
  title: "Dashboard",
  subtitle: "Here is your CASC performance overview.",
  summaryTitle: "Performance overview",
  summaryCards: [
    {
      ...STRONG,
      title: "Pass Rate",
      description:
        "Percentage of stations passed with ≥80% competencies in each domain",
    },
    {
      ...GROWTH,
      title: "Fail Rate",
      description:
        "Percentage of stations not meeting minimum competency requirements",
      icon: "critical",
    },
  ],
  domains: {
    subtitle: "Competency rate by domain",
    maxScore: 1,
    threshold: 0.8,
    thresholdLabel: "Pass threshold",
    ticks: [0, 0.2, 0.4, 0.6, 0.8, 1],
    percent: true,
    decimals: 1,
    layout: "horizontal",
    yAxisWidth: 150,
    colors: {
      "History Taking": "#4ade80",
      Examination: b2cDesignTokens.accent.DEFAULT,
      Management: "#f97316",
      Communication: "#8b5cf6",
    },
  },
  trend: {
    subtitle: "Competency over time",
    maxScore: 100,
    threshold: 80,
    thresholdLabel: "Pass (80%)",
    ticks: [0, 20, 40, 60, 80, 100],
    decimals: 1,
    unit: "%",
  },
  sections: NO_EXTRA_SECTIONS,
};

const ORTHO: ExamConfig = {
  code: "ortho",
  label: "Orthopaedic ST3",
  eventNoun: "interview",
  title: "Dashboard",
  subtitle: "Here is your interview performance overview.",
  summaryTitle: "Performance overview",
  summaryCards: [STRONG, GROWTH],
  domains: {
    subtitle: "Scores by station type or domain",
    maxScore: 10,
    threshold: 7,
    thresholdLabel: "Good (7/10)",
    ticks: [0, 2, 4, 6, 8, 10],
    decimals: 1,
    unit: "/ 10",
    layout: "vertical",
    height: 320,
    palette: ["#4ade80", b2cDesignTokens.accent.DEFAULT, "#f97316", "#8b5cf6", "#06b6d4"],
    groupByStationType: true,
  },
  trend: {
    subtitle: "Station score over time",
    maxScore: 50,
    threshold: 35,
    thresholdLabel: "Pass (35/50)",
    ticks: [0, 10, 20, 30, 35, 40, 50],
    decimals: 0,
    unit: "/ 50",
  },
  sections: NO_EXTRA_SECTIONS,
};

const SCA: ExamConfig = {
  code: "sca",
  label: "SCA",
  eventNoun: "exam",
  title: "Where you stand",
  subtitle: null,
  summaryTitle: "Performance overview",
  /* The hero carries the split; SCA never had the stat cards. */
  summaryCards: [],
  domains: {
    subtitle: "Competent share by clinical domain",
    maxScore: 1,
    ticks: [0, 0.2, 0.4, 0.6, 0.8, 1],
    percent: true,
    decimals: 0,
    layout: "horizontal",
    yAxisWidth: 150,
    colors: {
      "Global skills": b2cDesignTokens.accent.DEFAULT,
      Tasks: "#4ade80",
      "Relating to others": "#8b5cf6",
    },
  },
  trend: {
    subtitle: "Competency over time",
    maxScore: 100,
    ticks: [0, 20, 40, 60, 80, 100],
    decimals: 0,
    unit: "%",
  },
  sections: { hero: true, weeklyTrend: true, insights: true, firstStation: true },
};

export const EXAM_CONFIGS: Record<string, ExamConfig> = {
  sca: SCA,
  plab: PLAB,
  casc: CASC,
  ortho: ORTHO,
};

/**
 * An exam the catalogue serves but this table does not name still gets a
 * dashboard: the platform's exams are authored now, so a new one appears
 * without a frontend release. It draws on whatever scale `/me/performance`
 * reports rather than guessing a threshold it has no basis for.
 */
export function configFor(examCode: string): ExamConfig {
  const known = EXAM_CONFIGS[examCode.toLowerCase()];
  if (known) return known;
  return {
    ...PLAB,
    code: examCode,
    label: examCode.toUpperCase(),
    subtitle: `Here is your ${examCode.toUpperCase()} performance overview.`,
    domains: {
      subtitle: "Average score by domain",
      maxScore: 1,
      ticks: [0, 0.2, 0.4, 0.6, 0.8, 1],
      percent: true,
      decimals: 0,
      layout: "horizontal",
      yAxisWidth: 150,
      palette: [chartColors.primary, chartColors.green, chartColors.amber, chartColors.indigo],
    },
    trend: {
      subtitle: "Score over time",
      maxScore: 100,
      ticks: [0, 20, 40, 60, 80, 100],
      decimals: 0,
      unit: "%",
    },
  };
}

/** The value as the exam's own scale writes it, for a tooltip or a bar label. */
export function formatScore(scale: ExamChartScale, value: number): string {
  if (scale.percent) return `${(value * 100).toFixed(scale.decimals ?? 0)}%`;
  const text = value.toFixed(scale.decimals ?? 1);
  if (!scale.unit) return text;
  return scale.unit.startsWith("%") ? `${text}${scale.unit}` : `${text} ${scale.unit}`;
}

/** Axis ticks, which are percentages where the values are proportions. */
export function formatTick(scale: ExamChartScale, value: number): string {
  return scale.percent ? `${Math.round(value * 100)}%` : String(value);
}
