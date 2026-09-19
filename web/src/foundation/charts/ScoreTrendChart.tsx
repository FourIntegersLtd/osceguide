"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
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
  chartMargin,
  chartTooltipStyle,
} from "./chartTheme";

export interface ScoreTrendPoint {
  label: string;
  score: number;
  meta?: string;
  color?: string;
}

interface ScoreTrendChartProps {
  data: ScoreTrendPoint[];
  maxScore: number;
  threshold?: number;
  thresholdLabel?: string;
  formatValue?: (value: number) => string;
  height?: number;
  ticks?: number[];
  stroke?: string;
}

export default function ScoreTrendChart({
  data,
  maxScore,
  threshold,
  thresholdLabel,
  formatValue = (v) => v.toFixed(1),
  height = CHART_HEIGHT,
  ticks,
  stroke = chartColors.primary,
}: ScoreTrendChartProps) {
  if (!data.length) return <ChartEmptyState height={height} />;

  const allZero = data.every((d) => !d.score);
  if (allZero) {
    return (
      <ChartEmptyState
        height={height}
        message="No trend data yet"
        hint="Scores will appear after completed stations"
      />
    );
  }

  return (
    <div className="w-full" style={{ height }}>
      <ResponsiveContainer>
        <LineChart data={data} margin={chartMargin}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke={chartColors.grid}
            vertical={false}
          />
          <XAxis
            dataKey="label"
            tick={chartAxisTick}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
            minTickGap={24}
          />
          <YAxis
            domain={[0, maxScore]}
            ticks={ticks}
            tick={chartAxisTick}
            tickLine={false}
            axisLine={false}
            width={36}
            allowDecimals={false}
          />
          <Tooltip
            formatter={(value: number, _name: string, item) => {
              const meta = item?.payload?.meta as string | undefined;
              return [formatValue(value), meta || "Score"];
            }}
            contentStyle={chartTooltipStyle}
          />
          <Line
            type="monotone"
            dataKey="score"
            stroke={stroke}
            strokeWidth={2}
            dot={(props) => {
              const { cx, cy, payload, index } = props;
              const fill =
                (payload as ScoreTrendPoint | undefined)?.color || stroke;
              if (typeof cx !== "number" || typeof cy !== "number") {
                return <g key={`dot-${index}`} />;
              }
              return (
                <circle
                  key={`dot-${index}`}
                  cx={cx}
                  cy={cy}
                  r={3.5}
                  fill={fill}
                  stroke="#fff"
                  strokeWidth={1.5}
                />
              );
            }}
            activeDot={{ r: 5 }}
          />
          {typeof threshold === "number" && (
            <ReferenceLine
              y={threshold}
              stroke={chartColors.green}
              strokeDasharray="4 4"
              label={
                thresholdLabel
                  ? {
                      value: thresholdLabel,
                      position: "insideTopRight",
                      fill: chartColors.axis,
                      fontSize: 10,
                    }
                  : undefined
              }
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
