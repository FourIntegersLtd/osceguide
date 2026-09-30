/** B2C dashboard chart tokens — ink + brand blue accent, vivid RAG band fills. */

import type { CSSProperties } from "react";
import { b2cDesignTokens } from "@/foundation/ui/designTokens";

export const CHART_HEIGHT = 220;

/** Design-system band fills (scores only — not chrome). */
export const bandChartColors = {
  competent: b2cDesignTokens.band.competent,
  developing: b2cDesignTokens.band.developing,
  development: b2cDesignTokens.band.development,
  competentBg: b2cDesignTokens.band.competentBg,
  developingBg: b2cDesignTokens.band.developingBg,
  developmentBg: b2cDesignTokens.band.developmentBg,
} as const;

export const chartColors = {
  primary: b2cDesignTokens.accent.DEFAULT,
  primarySoft: b2cDesignTokens.accent.DEFAULT,
  primaryMuted: b2cDesignTokens.accent.subtle,
  red: bandChartColors.development,
  amber: bandChartColors.developing,
  green: bandChartColors.competent,
  /** Muted indigo — distinct from brand blue for categorical series (funnel mid-step). */
  indigo: "#5b4e9e",
  sky: b2cDesignTokens.accent.DEFAULT,
  slate: b2cDesignTokens.ink[400],
  muted: b2cDesignTokens.ink[400],
  grid: b2cDesignTokens.border.light,
  axis: b2cDesignTokens.ink[500],
  axisLine: b2cDesignTokens.border.DEFAULT,
  border: b2cDesignTokens.border.DEFAULT,
  text: b2cDesignTokens.ink[900],
} as const;

/** Visit → sign-up → payment. Each step is a different hue so the funnel is scannable. */
export const funnelStepColors = {
  landing: chartColors.primary,
  signup: chartColors.indigo,
  purchase: chartColors.green,
} as const;

export const ragSeries = {
  red: { key: "Requires Development", color: chartColors.red },
  amber: { key: "Developing Competency", color: chartColors.amber },
  green: { key: "Competent", color: chartColors.green },
} as const;

export const chartTooltipStyle: CSSProperties = {
  backgroundColor: "#ffffff",
  borderRadius: 8,
  border: `1px solid ${chartColors.border}`,
  padding: "6px 10px",
  fontSize: 12,
  color: chartColors.text,
  boxShadow: "none",
};

export const chartAxisTick = {
  fill: chartColors.axis,
  fontSize: 10,
} as const;

export const chartMargin = {
  top: 4,
  right: 4,
  left: -16,
  bottom: 0,
} as const;

/** Tighter margins for narrow viewports — avoids horizontal overflow from Recharts. */
export const chartMarginNarrow = {
  top: 4,
  right: 4,
  left: 0,
  bottom: 0,
} as const;

export const chartMarginLabeled = {
  top: 4,
  right: 8,
  left: 4,
  bottom: 0,
} as const;

export function truncateLabel(label: string, max = 18): string {
  if (label.length <= max) return label;
  return `${label.slice(0, max - 1)}…`;
}

/** Abbreviated day labels for trend X axes (e.g. 12 Jan). */
export function shortChartDate(isoOrLabel: string): string {
  const d = new Date(isoOrLabel);
  if (Number.isNaN(d.getTime())) return truncateLabel(isoOrLabel, 10);
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}
