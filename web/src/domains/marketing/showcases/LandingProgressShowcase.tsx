import { b2cDesignTokens } from "@/domains/marketing/support/designTokens";
import type { ExamShowcaseVariant } from "./examShowcaseContent";
import {
  getProgressShowcaseContent,
  type ProgressCategoryPoint,
  type ProgressRagSplit,
} from "./progressShowcaseContent";

/**
 * Static stand-in for the signed-in progress dashboard, built from mock content
 * rather than a screenshot so it stays responsive, on-token and indexable.
 * Deliberately free of hooks and chart libraries — it renders on the server.
 */

const BAND_FILL = {
  competent: b2cDesignTokens.band.competent,
  developing: b2cDesignTokens.band.developing,
  development: b2cDesignTokens.band.development,
} as const;

const BAND_LEGEND = [
  { key: "development", label: "Requires Development" },
  { key: "developing", label: "Developing Competency" },
  { key: "competent", label: "Competent" },
] as const;

const CARD =
  "rounded-[var(--landing-radius-card,0.5rem)] border border-landing-warm bg-landing-card p-4 shadow-landing-showcase-side sm:p-5";

function Eyebrow({ children }: { children: string }) {
  return (
    <div className="font-landing-mono text-[9px] font-medium uppercase tracking-[0.14em] text-b2c-text-muted sm:text-[10px]">
      {children}
    </div>
  );
}

/** Conic ring in competent → developing → development order, matching the app. */
function CompetencyDonut({ split }: { split: ProgressRagSplit }) {
  const competentEnd = split.competent;
  const developingEnd = split.competent + split.developing;

  return (
    <div
      className="relative h-[104px] w-[104px] shrink-0 rounded-full shadow-[0_2px_8px_rgba(16,24,40,0.08)] sm:h-[132px] sm:w-[132px]"
      style={{
        background: `conic-gradient(${BAND_FILL.competent} 0 ${competentEnd}%, ${BAND_FILL.developing} ${competentEnd}% ${developingEnd}%, ${BAND_FILL.development} ${developingEnd}% 100%)`,
      }}
    >
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="flex h-[76px] w-[76px] flex-col items-center justify-center rounded-full bg-landing-card sm:h-24 sm:w-24">
          <span className="font-landing-heading text-xl font-semibold tracking-[-0.03em] text-osce-ink-900 sm:text-2xl">
            {split.development}%
          </span>
          <span className="mt-0.5 font-landing-mono text-[8px] font-medium uppercase tracking-[0.12em] text-b2c-text-muted sm:text-[9px]">
            Development
          </span>
        </div>
      </div>
    </div>
  );
}

/**
 * Eight weekly bars. The oldest half stays grey and only the most recent weeks
 * take the accent, so the eye reads left-to-right as recency, not as ranking.
 */
function TrendBars({ weeks }: { weeks: number[] }) {
  const peak = Math.max(...weeks, 1);

  return (
    <div className="flex h-20 items-end gap-[6px] sm:h-24 sm:gap-[7px]">
      {weeks.map((week, index) => {
        const hasData = week > 0;
        const position = weeks.length > 1 ? index / (weeks.length - 1) : 1;
        const fill = !hasData
          ? b2cDesignTokens.trendBar.empty
          : position < 0.5
            ? b2cDesignTokens.trendBar.empty
            : position < 0.75
              ? b2cDesignTokens.trendBar.mid
              : b2cDesignTokens.trendBar.active;

        return (
          <div
            key={index}
            className="flex-1 rounded-[2px]"
            style={{
              height: hasData ? `${Math.max(12, (week / peak) * 100)}%` : "10%",
              backgroundColor: fill,
              opacity: hasData ? 1 : 0.4,
            }}
          />
        );
      })}
    </div>
  );
}

const PLOT = { left: 36, right: 312, top: 12, bottom: 150 } as const;

/** Monotone-ish cubic through evenly spaced points, with flat control handles. */
function areaPath(points: Array<{ x: number; y: number }>): string {
  return points.reduce((path, point, index) => {
    if (index === 0) {
      return `M ${point.x},${point.y}`;
    }
    const previous = points[index - 1];
    const midX = (previous.x + point.x) / 2;
    return `${path} C ${midX},${previous.y} ${midX},${point.y} ${point.x},${point.y}`;
  }, "");
}

function CategoryChart({
  categories,
  axisMax,
}: {
  categories: ProgressCategoryPoint[];
  axisMax: number;
}) {
  const step =
    categories.length > 1
      ? (PLOT.right - PLOT.left) / (categories.length - 1)
      : 0;
  const points = categories.map((category, index) => ({
    x: PLOT.left + index * step,
    y: PLOT.bottom - (category.value / axisMax) * (PLOT.bottom - PLOT.top),
  }));
  const line = areaPath(points);
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((fraction) => ({
    value: Math.round(axisMax * fraction),
    y: PLOT.bottom - fraction * (PLOT.bottom - PLOT.top),
  }));

  return (
    <svg
      viewBox="0 0 320 196"
      className="h-auto w-full"
      role="img"
      aria-label={`Assessment volume by category: ${categories
        .map((c) => `${c.labelLines.join(" ")} ${c.value}`)
        .join(", ")}`}
    >
      <defs>
        <linearGradient id="landing-progress-area" x1="0" y1="0" x2="0" y2="1">
          <stop
            offset="0%"
            stopColor={b2cDesignTokens.accent.DEFAULT}
            stopOpacity="0.22"
          />
          <stop
            offset="100%"
            stopColor={b2cDesignTokens.accent.DEFAULT}
            stopOpacity="0.02"
          />
        </linearGradient>
      </defs>

      {ticks.map((tick) => (
        <g key={tick.value}>
          <line
            x1={PLOT.left}
            y1={tick.y}
            x2={PLOT.right}
            y2={tick.y}
            stroke={b2cDesignTokens.border.light}
            strokeWidth="1"
          />
          <text
            x={PLOT.left - 8}
            y={tick.y + 3}
            textAnchor="end"
            fontSize="9"
            fill={b2cDesignTokens.ink[500]}
          >
            {tick.value}
          </text>
        </g>
      ))}

      <path
        d={`${line} L ${points[points.length - 1].x},${PLOT.bottom} L ${points[0].x},${PLOT.bottom} Z`}
        fill="url(#landing-progress-area)"
      />
      <path
        d={line}
        fill="none"
        stroke={b2cDesignTokens.accent.DEFAULT}
        strokeWidth="2"
        strokeLinecap="round"
      />

      {points.map((point, index) => (
        <circle
          key={index}
          cx={point.x}
          cy={point.y}
          r="3"
          fill={b2cDesignTokens.accent.DEFAULT}
        />
      ))}

      {categories.map((category, index) => (
        <text
          key={category.labelLines.join(" ")}
          x={points[index].x}
          y={PLOT.bottom + 18}
          textAnchor="middle"
          fontSize="9"
          fill={b2cDesignTokens.ink[500]}
        >
          {category.labelLines.map((line, lineIndex) => (
            <tspan
              key={line}
              x={points[index].x}
              dy={lineIndex === 0 ? 0 : 11}
            >
              {line}
            </tspan>
          ))}
        </text>
      ))}
    </svg>
  );
}

type LandingProgressShowcaseProps = {
  variant?: ExamShowcaseVariant;
  className?: string;
};

export function LandingProgressShowcase({
  variant = "sca",
  className = "",
}: LandingProgressShowcaseProps) {
  const content = getProgressShowcaseContent(variant);

  return (
    <figure className={`m-0 ${className}`}>
      <div className="overflow-hidden rounded-[var(--landing-radius-panel,10px)] border border-landing-warm bg-landing-card-muted p-4 text-left shadow-landing-panel sm:p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
          <div className="min-w-0">
            <Eyebrow>{content.eyebrow}</Eyebrow>
            <h3 className="mt-1.5 font-landing-heading text-lg font-semibold leading-tight tracking-[-0.025em] text-osce-ink-900 sm:text-2xl">
              {content.title}
            </h3>
            <p className="mt-1 font-landing-body text-xs text-b2c-text-secondary sm:text-sm">
              {content.subtitle}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2.5">
            <span className="font-landing-body text-[11px] text-b2c-text-secondary sm:text-xs">
              {content.examDateLabel}
            </span>
            <span className="rounded-lg bg-osce-accent px-2.5 py-1.5 font-landing-body text-[11px] font-medium text-white sm:px-3 sm:text-xs">
              {content.ctaLabel}
            </span>
          </div>
        </div>

        <div className="mt-4 flex items-center gap-1 border-b border-b2c-border-light pb-3 sm:mt-5">
          <span className="rounded-md bg-landing-card px-2.5 py-1 font-landing-body text-[11px] font-medium text-osce-ink-900 shadow-landing-showcase-side sm:text-xs">
            Overview
          </span>
          <span className="px-2.5 py-1 font-landing-body text-[11px] text-b2c-text-muted sm:text-xs">
            Trends
          </span>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-3 sm:mt-5 sm:gap-4 lg:grid-cols-[1fr_260px]">
          <div className={CARD}>
            <Eyebrow>Competency</Eyebrow>
            <div className="mt-4 flex flex-col items-center gap-5 sm:flex-row sm:gap-6">
              <CompetencyDonut split={content.competency} />
              <div className="min-w-0 flex-1">
                <p className="font-landing-body text-xs leading-relaxed text-b2c-text-secondary sm:text-sm">
                  <span className="font-medium text-osce-ink-900">
                    {content.competency.competent}%
                  </span>{" "}
                  of your assessed marks now meet the competent standard.
                </p>
                <div className="mt-4 flex flex-wrap gap-4 sm:gap-6">
                  {BAND_LEGEND.map((band) => (
                    <div key={band.key}>
                      <div className="flex items-center gap-1.5">
                        <span
                          className="h-2 w-2 shrink-0 rounded-[2px]"
                          style={{ backgroundColor: BAND_FILL[band.key] }}
                        />
                        <span className="font-landing-heading text-base font-semibold tracking-[-0.02em] text-osce-ink-900 sm:text-xl">
                          {content.competency[band.key]}%
                        </span>
                      </div>
                      <p className="mt-0.5 font-landing-mono text-[8px] font-medium uppercase tracking-[0.12em] text-b2c-text-muted sm:text-[9px]">
                        {band.key === "development"
                          ? "Development"
                          : band.key === "developing"
                            ? "Developing"
                            : "Competent"}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className={CARD}>
            <Eyebrow>Trend · last 8 weeks</Eyebrow>
            <div className="mt-4">
              <TrendBars weeks={content.weeklyTrend} />
            </div>
            <p className="mt-2.5 font-landing-body text-[11px] leading-relaxed text-b2c-text-secondary sm:text-xs">
              How much of your work met the competent standard each week. Left
              is eight weeks ago, right is this week.
            </p>
          </div>
        </div>

        <div className="mt-3 grid grid-cols-1 gap-3 sm:mt-4 sm:gap-4 lg:grid-cols-[1fr_360px]">
          <div className={CARD}>
            <Eyebrow>Domains</Eyebrow>
            <p className="mt-1 font-landing-body text-[11px] text-b2c-text-secondary sm:text-xs">
              RAG mix by clinical domain
            </p>

            <div className="mt-5 space-y-4">
              {content.domains.map((row) => (
                <div
                  key={row.label}
                  className="flex items-center gap-3 sm:gap-4"
                >
                  <div className="w-[68px] shrink-0 text-right font-landing-body text-[10px] leading-tight text-b2c-text-secondary sm:w-24 sm:text-[11px]">
                    {row.label}
                  </div>
                  <div className="flex h-5 min-w-0 flex-1 overflow-hidden rounded-[3px] sm:h-6">
                    {BAND_LEGEND.map((band) => (
                      <div
                        key={band.key}
                        style={{
                          width: `${row.split[band.key]}%`,
                          backgroundColor: BAND_FILL[band.key],
                        }}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-2 flex justify-between pl-[80px] font-landing-mono text-[8px] text-b2c-text-muted sm:pl-[112px] sm:text-[9px]">
              {["0%", "25%", "50%", "75%", "100%"].map((tick) => (
                <span key={tick}>{tick}</span>
              ))}
            </div>

            <div className="mt-4 flex flex-wrap justify-center gap-x-4 gap-y-1.5 border-t border-b2c-border-light pt-3">
              {BAND_LEGEND.map((band) => (
                <span
                  key={band.key}
                  className="flex items-center gap-1.5 font-landing-body text-[10px] sm:text-[11px]"
                  style={{ color: BAND_FILL[band.key] }}
                >
                  <span
                    className="h-2 w-2 shrink-0 rounded-[2px]"
                    style={{ backgroundColor: BAND_FILL[band.key] }}
                  />
                  {band.label}
                </span>
              ))}
            </div>
          </div>

          <div className={CARD}>
            <Eyebrow>Categories</Eyebrow>
            <p className="mt-1 font-landing-body text-[11px] text-b2c-text-secondary sm:text-xs">
              Assessment volume by category
            </p>
            <div className="mt-4">
              <CategoryChart
                categories={content.categories}
                axisMax={content.categoryAxisMax}
              />
            </div>
          </div>
        </div>
      </div>

      <figcaption className="mt-3 text-center font-landing-body text-[11px] text-b2c-text-muted">
        {content.caption}
      </figcaption>
    </figure>
  );
}
