"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import ChartEmptyState from "./ChartEmptyState";
import {
  chartAxisTick,
  chartColors,
  chartMarginLabeled,
  chartTooltipStyle,
  truncateLabel,
} from "./chartTheme";

interface SkillChange {
  category: string;
  from: number;
  to: number;
}

interface SkillBeforeAfterChartProps {
  improvements: SkillChange[];
  regressions: SkillChange[];
  stagnations: { category: string; value: number }[];
  skillLabels?: Record<string, string>;
  height?: number;
}

type Row = {
  skill: string;
  earlier: number;
  latest: number;
  delta: number;
};

function toPct(v: number): number {
  return Math.round(Number(v) * 100);
}

/**
 * Side-by-side earlier vs latest scores. much easier to read than slope/dumbbells.
 */
export default function SkillBeforeAfterChart({
  improvements,
  regressions,
  stagnations,
  skillLabels = {},
  height = 280,
}: SkillBeforeAfterChartProps) {
  const label = (raw: string) =>
    skillLabels[raw] || raw.replace(/_/g, " ");

  const rows: Row[] = [
    ...improvements.map((r) => ({
      skill: label(r.category),
      earlier: toPct(r.from),
      latest: toPct(r.to),
      delta: toPct(r.to) - toPct(r.from),
    })),
    ...regressions.map((r) => ({
      skill: label(r.category),
      earlier: toPct(r.from),
      latest: toPct(r.to),
      delta: toPct(r.to) - toPct(r.from),
    })),
    ...stagnations.map((r) => {
      const v = toPct(r.value);
      return {
        skill: label(r.category),
        earlier: v,
        latest: v,
        delta: 0,
      };
    }),
  ]
    .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))
    .slice(0, 8);

  if (!rows.length) {
    return (
      <ChartEmptyState
        height={height}
        message="No skill changes yet"
        hint="Complete more sessions to compare earlier and latest scores"
      />
    );
  }

  const plotHeight = Math.max(height, 64 + rows.length * 44);

  return (
    <div className="w-full">
      <div className="mb-3 flex flex-wrap items-center gap-4 text-osce-caption text-b2c-text-muted">
        <span className="inline-flex items-center gap-1.5">
          <span
            className="h-2.5 w-2.5 rounded-sm"
            style={{ backgroundColor: chartColors.slate }}
            aria-hidden
          />
          Earlier
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span
            className="h-2.5 w-2.5 rounded-sm"
            style={{ backgroundColor: chartColors.primary }}
            aria-hidden
          />
          Latest
        </span>
      </div>

      <div style={{ height: plotHeight }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={rows}
            layout="vertical"
            margin={{ ...chartMarginLabeled, left: 8 }}
            barCategoryGap="18%"
            barGap={4}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke={chartColors.grid}
              horizontal={false}
            />
            <XAxis
              type="number"
              domain={[0, 100]}
              tick={chartAxisTick}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `${v}%`}
            />
            <YAxis
              type="category"
              dataKey="skill"
              width={120}
              tickFormatter={(v) => truncateLabel(String(v), 18)}
              tick={chartAxisTick}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              contentStyle={chartTooltipStyle}
              formatter={(value: number, name: string) => [
                `${value}%`,
                name === "earlier" ? "Earlier" : "Latest",
              ]}
              labelFormatter={(label, payload) => {
                const row = payload?.[0]?.payload as Row | undefined;
                if (!row) return String(label);
                const sign = row.delta > 0 ? "+" : "";
                return `${row.skill}  (${sign}${row.delta} pts)`;
              }}
            />
            <Bar
              dataKey="earlier"
              name="earlier"
              fill={chartColors.slate}
              maxBarSize={14}
              radius={[0, 3, 3, 0]}
            />
            <Bar
              dataKey="latest"
              name="latest"
              maxBarSize={14}
              radius={[0, 3, 3, 0]}
            >
              {rows.map((row) => (
                <Cell
                  key={row.skill}
                  fill={
                    row.delta > 0
                      ? chartColors.green
                      : row.delta < 0
                        ? chartColors.red
                        : chartColors.primary
                  }
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <p className="mt-2 text-center text-osce-caption text-b2c-text-muted">
        Grey = earlier score · Coloured = latest (green up, red down)
      </p>
    </div>
  );
}
