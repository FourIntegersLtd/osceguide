"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import ChartEmptyState from "./ChartEmptyState";
import { percentSplit } from "./ragSplit";
import {
  chartAxisTick,
  chartColors,
  chartTooltipStyle,
  truncateLabel,
} from "./chartTheme";

export interface RagRow {
  name: string;
  "Requires Development": number;
  "Developing Competency": number;
  Competent: number;
}

interface RagCompositionBarsProps {
  data: RagRow[];
  /** When true, each row stacks to 100% (domain mix). When false, raw counts. */
  stackedPercent?: boolean;
  height?: number;
  yAxisWidth?: number;
  emptyMessage?: string;
  emptyHint?: string;
}

type ChartRow = {
  name: string;
  fullName: string;
  red: number;
  amber: number;
  green: number;
};

const SERIES = [
  { key: "red" as const, label: "Requires Development", color: chartColors.red },
  { key: "amber" as const, label: "Developing Competency", color: chartColors.amber },
  { key: "green" as const, label: "Competent", color: chartColors.green },
];

/**
 * Horizontal 100% stacked RAG bars (domains) or raw stacked counts.
 * Uses short dataKeys so Recharts reliably paints segments.
 */
export default function RagCompositionBars({
  data,
  stackedPercent = true,
  height = 260,
  yAxisWidth = 118,
  emptyMessage = "No scores yet",
  emptyHint = "Complete SCA stations to see your RAG mix here",
}: RagCompositionBarsProps) {
  const chartData: ChartRow[] = data
    .map((row) => {
      const r = Number(row["Requires Development"] || 0);
      const a = Number(row["Developing Competency"] || 0);
      const g = Number(row.Competent || 0);
      const total = r + a + g;
      if (total <= 0) return null;
      if (!stackedPercent) {
        return {
          name: truncateLabel(row.name, 18),
          fullName: row.name,
          red: r,
          amber: a,
          green: g,
        };
      }
      return {
        name: truncateLabel(row.name, 18),
        fullName: row.name,
        ...percentSplit(r, a, g),
      };
    })
    .filter((row): row is ChartRow => row !== null);

  if (!chartData.length) {
    return (
      <ChartEmptyState
        height={height}
        message={emptyMessage}
        hint={emptyHint}
      />
    );
  }

  const plotHeight = Math.max(height, 72 + chartData.length * 48);
  const suffix = stackedPercent ? "%" : "";

  return (
    <div className="w-full" style={{ width: "100%", height: plotHeight }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 4, right: 16, left: 4, bottom: 4 }}
          barCategoryGap="28%"
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke={chartColors.grid}
            horizontal={false}
          />
          <XAxis
            type="number"
            domain={stackedPercent ? [0, 100] : [0, "dataMax"]}
            tick={chartAxisTick}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `${v}${suffix}`}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={yAxisWidth}
            tick={chartAxisTick}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            cursor={{ fill: "rgba(58, 93, 143, 0.08)" }}
            contentStyle={chartTooltipStyle}
            labelFormatter={(_, payload) =>
              String(payload?.[0]?.payload?.fullName || "")
            }
            formatter={(value: number, name: string) => {
              const series = SERIES.find((s) => s.key === name);
              return [
                `${Number(value).toFixed(stackedPercent ? 1 : 0)}${suffix}`,
                series?.label || name,
              ];
            }}
          />
          <Legend
            verticalAlign="bottom"
            iconType="square"
            iconSize={8}
            wrapperStyle={{
              paddingTop: 12,
              fontSize: 11,
              color: chartColors.axis,
            }}
            formatter={(value) => {
              const series = SERIES.find((s) => s.key === value);
              return series?.label || value;
            }}
          />
          {SERIES.map((series, index) => (
            <Bar
              key={series.key}
              dataKey={series.key}
              name={series.key}
              stackId="rag"
              fill={series.color}
              barSize={22}
              radius={
                index === SERIES.length - 1 ? [0, 4, 4, 0] : [0, 0, 0, 0]
              }
              isAnimationActive={false}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
