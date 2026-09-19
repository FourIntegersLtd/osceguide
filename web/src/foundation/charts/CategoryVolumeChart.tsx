"use client";

import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import ChartEmptyState from "./ChartEmptyState";
import {
  chartAxisTick,
  chartColors,
  chartTooltipStyle,
} from "./chartTheme";
import type { RagRow } from "./RagCompositionBars";

interface CategoryVolumeChartProps {
  data: RagRow[];
  height?: number;
  emptyMessage?: string;
  emptyHint?: string;
}

type VolumeRow = {
  name: string;
  fullName: string;
  total: number;
};

const CATEGORY_LABEL_MAX_CHARS = 14;

function wrapCategoryLabel(label: string): string[] {
  const words = label.trim().split(/\s+/).filter(Boolean);
  if (!words.length) return [""];

  const lines: string[] = [];
  let current = "";

  for (const word of words) {
    const candidate = current ? `${current} ${word}` : word;
    if (candidate.length <= CATEGORY_LABEL_MAX_CHARS) {
      current = candidate;
      continue;
    }
    if (current) lines.push(current);
    current = word;
  }
  if (current) lines.push(current);

  return lines.slice(0, 2);
}

function CategoryVolumeXAxisTick(tickCount: number) {
  return function Tick(props: {
    x?: number;
    y?: number;
    payload?: { value: string };
    index?: number;
  }) {
    const { x = 0, y = 0, payload, index = 0 } = props;
    const lines = wrapCategoryLabel(String(payload?.value ?? ""));
    const lineHeight = 13;
    const isFirst = index === 0;
    const isLast = index === tickCount - 1;
    const textAnchor = isFirst ? "start" : isLast ? "end" : "middle";

    return (
      <g transform={`translate(${x},${y + 10})`}>
        {lines.map((line, lineIndex) => (
          <text
            key={`${line}-${lineIndex}`}
            y={lineIndex * lineHeight}
            textAnchor={textAnchor}
            fill={chartColors.axis}
            fontSize={10}
          >
            {line}
          </text>
        ))}
      </g>
    );
  };
}

/**
 * Category volume as a line chart. score count per category.
 */
export default function CategoryVolumeChart({
  data,
  height = 280,
  emptyMessage = "No scores yet",
  emptyHint = "Complete SCA stations to see category volume here",
}: CategoryVolumeChartProps) {
  const chartData: VolumeRow[] = data
    .map((row) => {
      const total =
        Number(row["Requires Development"] || 0) +
        Number(row["Developing Competency"] || 0) +
        Number(row.Competent || 0);
      if (total <= 0) return null;
      return {
        name: row.name,
        fullName: row.name,
        total,
      };
    })
    .filter((row): row is VolumeRow => row !== null)
    .sort((a, b) => b.total - a.total);

  if (!chartData.length) {
    return (
      <ChartEmptyState
        height={height}
        message={emptyMessage}
        hint={emptyHint}
      />
    );
  }

  const maxLabelLines = Math.max(
    ...chartData.map((row) => wrapCategoryLabel(row.fullName).length),
    1,
  );
  const xAxisHeight = maxLabelLines > 1 ? 52 : 36;
  const chartBottomMargin = maxLabelLines > 1 ? 36 : 24;

  return (
    <div
      className="w-full min-w-0 overflow-visible px-1 sm:px-0 [&_.recharts-wrapper]:overflow-visible [&_.recharts-surface]:overflow-visible"
      style={{ width: "100%", height }}
    >
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart
          data={chartData}
          style={{ overflow: "visible" }}
          margin={{ top: 12, right: 20, left: 8, bottom: chartBottomMargin }}
        >
          <defs>
            <linearGradient id="categoryVolumeFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={chartColors.primary} stopOpacity={0.28} />
              <stop offset="100%" stopColor={chartColors.primary} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke={chartColors.grid}
            vertical={false}
          />
          <XAxis
            dataKey="name"
            tick={CategoryVolumeXAxisTick(chartData.length)}
            tickLine={false}
            axisLine={false}
            interval={0}
            height={xAxisHeight}
            padding={{ left: 16, right: 16 }}
          />
          <YAxis
            allowDecimals={false}
            tick={chartAxisTick}
            tickLine={false}
            axisLine={false}
            width={40}
          />
          <Tooltip
            cursor={{ stroke: chartColors.primaryMuted, strokeWidth: 1 }}
            contentStyle={chartTooltipStyle}
            labelFormatter={(_, payload) =>
              String(payload?.[0]?.payload?.fullName || "")
            }
            formatter={(value: number) => [
              Number(value).toLocaleString(),
              "Scores",
            ]}
          />
          <Area
            type="monotone"
            dataKey="total"
            fill="url(#categoryVolumeFill)"
            stroke="none"
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="total"
            name="Scores"
            stroke={chartColors.primary}
            strokeWidth={2.5}
            dot={{
              r: 4,
              fill: chartColors.primary,
              stroke: "#fff",
              strokeWidth: 2,
            }}
            activeDot={{ r: 6, fill: chartColors.primary }}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
