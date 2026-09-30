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
  CHART_HEIGHT,
  chartAxisTick,
  chartColors,
  chartMarginLabeled,
  chartTooltipStyle,
  truncateLabel,
} from "./chartTheme";

interface SkillSlopeChartProps {
  improvements: { category: string; from: number; to: number }[];
  regressions: { category: string; from: number; to: number }[];
  stagnations: { category: string; value: number }[];
  skillLabels?: Record<string, string>;
  height?: number;
}

type Row = {
  skill: string;
  from: number;
  to: number;
  delta: number;
  kind: "improvement" | "regression" | "stagnation";
  move: number;
  low: number;
};

function toPct(v: number): number {
  return Math.round(v * 100);
}

export default function SkillSlopeChart({
  improvements,
  regressions,
  stagnations,
  skillLabels = {},
  height = CHART_HEIGHT,
}: SkillSlopeChartProps) {
  const label = (raw: string) =>
    skillLabels[raw] || raw.replace(/_/g, " ");

  const rows: Row[] = [
    ...regressions.map((r) => {
      const from = toPct(r.from);
      const to = toPct(r.to);
      return {
        skill: label(r.category),
        from,
        to,
        delta: to - from,
        kind: "regression" as const,
        move: Math.abs(to - from) || 1,
        low: Math.min(from, to),
      };
    }),
    ...improvements.map((r) => {
      const from = toPct(r.from);
      const to = toPct(r.to);
      return {
        skill: label(r.category),
        from,
        to,
        delta: to - from,
        kind: "improvement" as const,
        move: Math.abs(to - from) || 1,
        low: Math.min(from, to),
      };
    }),
    ...stagnations.map((r) => {
      const v = toPct(r.value);
      return {
        skill: label(r.category),
        from: v,
        to: v,
        delta: 0,
        kind: "stagnation" as const,
        move: 1,
        low: v,
      };
    }),
  ].slice(0, 10);

  if (!rows.length) {
    return (
      <ChartEmptyState
        height={height}
        message="No skill changes yet"
        hint="Complete more sessions to see before/after skill movement"
      />
    );
  }

  const colorFor = (kind: Row["kind"]) => {
    if (kind === "improvement") return chartColors.green;
    if (kind === "regression") return chartColors.red;
    return chartColors.amber;
  };

  return (
    <div className="w-full" style={{ height }}>
      <ResponsiveContainer>
        <BarChart
          data={rows}
          layout="vertical"
          margin={chartMarginLabeled}
          barCategoryGap="28%"
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke={chartColors.grid}
            vertical={false}
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
            width={110}
            tickFormatter={(v) => truncateLabel(String(v), 16)}
            tick={chartAxisTick}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            contentStyle={chartTooltipStyle}
            formatter={(_value: number, _name: string, item) => {
              const row = item?.payload as Row | undefined;
              if (!row) return ["", ""];
              const arrow =
                row.delta > 0 ? "↑" : row.delta < 0 ? "↓" : "→";
              return [
                `${row.from}% ${arrow} ${row.to}%`,
                row.kind === "stagnation"
                  ? "Stable"
                  : row.kind === "improvement"
                    ? "Improving"
                    : "Declining",
              ];
            }}
          />
          {/* Invisible spacer to offset the range start */}
          <Bar
            dataKey="low"
            stackId="slope"
            fill="transparent"
            legendType="none"
            isAnimationActive={false}
          />
          <Bar
            dataKey="move"
            stackId="slope"
            legendType="none"
            isAnimationActive={false}
            shape={(props: {
              x?: number;
              y?: number;
              width?: number;
              height?: number;
              payload?: Row;
            }) => {
              const { x = 0, y = 0, width = 0, height: h = 0, payload } =
                props;
              if (!payload) return <g />;
              const color = colorFor(payload.kind);
              const midY = y + h / 2;
              const fromRatio =
                payload.move === 0
                  ? 0
                  : (payload.from - payload.low) / payload.move;
              const toRatio =
                payload.move === 0
                  ? 0
                  : (payload.to - payload.low) / payload.move;
              const fromX = x + width * fromRatio;
              const toX = x + width * toRatio;
              return (
                <g>
                  <line
                    x1={fromX}
                    y1={midY}
                    x2={toX}
                    y2={midY}
                    stroke={color}
                    strokeWidth={3}
                    strokeLinecap="round"
                  />
                  <circle
                    cx={fromX}
                    cy={midY}
                    r={4.5}
                    fill="#fff"
                    stroke={color}
                    strokeWidth={2}
                  />
                  <circle
                    cx={toX}
                    cy={midY}
                    r={5}
                    fill={color}
                    stroke="#fff"
                    strokeWidth={1.5}
                  />
                </g>
              );
            }}
          >
            {rows.map((row) => (
              <Cell key={row.skill} fill={colorFor(row.kind)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <p className="mt-2 text-center text-osce-caption text-b2c-text-muted">
        Hollow = earlier · Solid = latest
      </p>
    </div>
  );
}
