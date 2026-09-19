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
          {/*
            One axis element each, with orientation chosen in the props.

            These used to be two fragments in a ternary, and under React 19 the
            axes silently disappeared: recharts flattens its children with its
            own bundled `react-is@18`, which does not recognise React 19's
            element symbol, so everything inside a fragment was dropped. The
            bars drew and the scale and the pass line did not — a chart that
            looks fine and means nothing. Recharts has to see each axis as a
            direct child, so it gets one.
          */}
          <XAxis
            {...(isHorizontal
              ? {
                  type: "number" as const,
                  domain: [0, maxScore],
                  ticks,
                  tickFormatter: formatTick,
                }
              : {
                  dataKey: "label",
                  interval: "preserveStartEnd" as const,
                  minTickGap: 24,
                })}
            tick={chartAxisTick}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            {...(isHorizontal
              ? {
                  type: "category" as const,
                  dataKey: "label",
                  width: yAxisWidth,
                }
              : {
                  domain: [0, maxScore],
                  ticks,
                  tickFormatter: formatTick,
                  width: 36,
                  allowDecimals: false,
                })}
            tick={chartAxisTick}
            tickLine={false}
            axisLine={false}
          />
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
