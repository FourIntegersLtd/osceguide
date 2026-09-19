"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
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
  chartMarginLabeled,
  chartTooltipStyle,
  truncateLabel,
} from "./chartTheme";

export interface ThresholdBarDatum {
  name: string;
  score: number;
  color?: string;
}

interface ThresholdBarsProps {
  data: ThresholdBarDatum[];
  maxScore: number;
  threshold?: number;
  thresholdLabel?: string;
  formatValue?: (value: number) => string;
  formatTick?: (value: number) => string;
  layout?: "horizontal" | "vertical";
  height?: number;
  yAxisWidth?: number;
  ticks?: number[];
}

export default function ThresholdBars({
  data,
  maxScore,
  threshold,
  thresholdLabel = "Pass threshold",
  formatValue = (v) => v.toFixed(1),
  formatTick,
  layout = "horizontal",
  height = CHART_HEIGHT,
  yAxisWidth = 110,
  ticks,
}: ThresholdBarsProps) {
  if (!data.length) return <ChartEmptyState height={height} />;

  const allZero = data.every((d) => !d.score);
  if (allZero) {
    return (
      <ChartEmptyState
        height={height}
        message="No scores yet"
        hint="Complete stations to populate this chart"
      />
    );
  }

  const chartData = data.map((d) => ({
    ...d,
    label: truncateLabel(d.name, 16),
    fill: d.color || chartColors.primary,
  }));

  const isHorizontal = layout === "horizontal";
  const plotHeight = isHorizontal
    ? Math.max(height, Math.min(360, 40 + chartData.length * 36))
    : height;

  return (
    <div className="w-full" style={{ height: plotHeight }}>
      <ResponsiveContainer>
        <BarChart
          data={chartData}
          layout={isHorizontal ? "vertical" : "horizontal"}
          margin={chartMarginLabeled}
          barCategoryGap="24%"
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke={chartColors.grid}
            vertical={false}
            horizontal
          />
          {isHorizontal ? (
            <>
              <XAxis
                type="number"
                domain={[0, maxScore]}
                ticks={ticks}
                tick={chartAxisTick}
                tickLine={false}
                axisLine={false}
                tickFormatter={formatTick}
              />
              <YAxis
                type="category"
                dataKey="label"
                width={yAxisWidth}
                tick={chartAxisTick}
                tickLine={false}
                axisLine={false}
              />
            </>
          ) : (
            <>
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
                tickFormatter={formatTick}
                width={36}
                allowDecimals={false}
              />
            </>
          )}
          <Tooltip
            formatter={(value: number) => [formatValue(value), "Score"]}
            labelFormatter={(label, payload) =>
              String(payload?.[0]?.payload?.name || label)
            }
            contentStyle={chartTooltipStyle}
            cursor={{ fill: "rgba(37, 99, 235, 0.06)" }}
          />
          <Bar
            dataKey="score"
            radius={isHorizontal ? [0, 4, 4, 0] : [4, 4, 0, 0]}
            maxBarSize={isHorizontal ? 28 : 32}
          >
            {chartData.map((entry) => (
              <Cell key={entry.name} fill={entry.fill} />
            ))}
          </Bar>
          {typeof threshold === "number" && (
            <ReferenceLine
              {...(isHorizontal ? { x: threshold } : { y: threshold })}
              stroke={chartColors.amber}
              strokeDasharray="4 4"
              label={{
                value: thresholdLabel,
                position: isHorizontal ? "insideBottomRight" : "insideTopRight",
                fill: chartColors.axis,
                fontSize: 10,
              }}
            />
          )}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
