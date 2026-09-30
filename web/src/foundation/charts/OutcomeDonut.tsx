"use client";

import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import ChartEmptyState from "./ChartEmptyState";
import {
  CHART_HEIGHT,
  bandChartColors,
  chartColors,
  chartTooltipStyle,
} from "./chartTheme";

export interface OutcomeSlice {
  name: string;
  value: number;
  color: string;
}

interface OutcomeDonutProps {
  data: OutcomeSlice[];
  centerLabel?: string;
  centerValue?: string;
  height?: number;
  showLegend?: boolean;
}

export default function OutcomeDonut({
  data,
  centerLabel,
  centerValue,
  height = CHART_HEIGHT,
  showLegend = true,
}: OutcomeDonutProps) {
  const filtered = data.filter((d) => d.value > 0);
  if (filtered.length === 0) {
    return <ChartEmptyState height={height} />;
  }

  const total = filtered.reduce((sum, d) => sum + d.value, 0);

  return (
    <div className="w-full">
      <div className="relative w-full" style={{ height }}>
        <ResponsiveContainer>
          <PieChart>
            <Pie
              data={filtered}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={52}
              outerRadius={78}
              paddingAngle={2}
              strokeWidth={0}
            >
              {filtered.map((entry) => (
                <Cell key={entry.name} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number, name: string) => {
                const pct = total > 0 ? Math.round((value / total) * 100) : 0;
                return [`${pct}%`, name];
              }}
              contentStyle={chartTooltipStyle}
            />
          </PieChart>
        </ResponsiveContainer>
        {(centerLabel || centerValue) && (
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
            {centerValue && (
              <p className="font-mono text-osce-heading font-medium leading-none text-osce-ink-900">
                {centerValue}
              </p>
            )}
            {centerLabel && (
              <p className="mt-1 font-mono text-osce-micro uppercase tracking-[0.08em] text-b2c-text-muted">
                {centerLabel}
              </p>
            )}
          </div>
        )}
      </div>
      {showLegend ? (
        <ul className="mt-1 flex flex-wrap items-center justify-center gap-x-3 gap-y-1">
          {filtered.map((slice) => {
            const short =
              slice.name === "Requires Development"
                ? "Development"
                : slice.name === "Developing Competency" ||
                    slice.name === "Developing"
                  ? "Developing"
                  : slice.name;
            return (
              <li
                key={slice.name}
                className="flex items-center gap-1.5 text-osce-caption text-b2c-text-muted"
              >
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ backgroundColor: slice.color }}
                  aria-hidden
                />
                {short}
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}

export const defaultRagSlices = (
  red: number,
  amber: number,
  green: number,
): OutcomeSlice[] => [
  {
    name: "Requires Development",
    value: red,
    color: bandChartColors.development,
  },
  { name: "Developing", value: amber, color: bandChartColors.developing },
  { name: "Competent", value: green, color: bandChartColors.competent },
];

export const defaultPassFailSlices = (
  pass: number,
  fail: number,
): OutcomeSlice[] => [
  { name: "Strong", value: pass, color: chartColors.green },
  { name: "Growth needed", value: fail, color: chartColors.red },
];
