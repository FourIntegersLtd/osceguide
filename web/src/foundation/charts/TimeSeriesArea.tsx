"use client";

import { useId } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  CHART_HEIGHT,
  chartAxisTick,
  chartColors,
  chartMarginNarrow,
  chartTooltipStyle,
} from "@/foundation/charts/chartTheme";
import {
  timeSeriesDomainMax,
  type TimeSeriesDatum,
  type TimeSeriesProps,
} from "@/foundation/charts/TimeSeriesBars";

/**
 * The same series as `TimeSeriesBars`, drawn as a soft filled area, or as a
 * plain line with `line` for a measure that should not read as a volume
 * (money over time). Dots carry a white ring so a single point still shows.
 */
export default function TimeSeriesArea({
  data,
  color,
  seriesName,
  formatValue,
  formatTick,
  wholeNumbers = true,
  yAxisWidth = 36,
  height = CHART_HEIGHT,
  line = false,
}: TimeSeriesProps & { line?: boolean }) {
  const gradientId = useId();
  const dot = { r: 3, fill: color, stroke: "#ffffff", strokeWidth: 2 };
  const shared = (
    <>
      <CartesianGrid stroke={chartColors.grid} vertical={false} />
      <XAxis
        dataKey="label"
        tick={chartAxisTick}
        tickLine={false}
        axisLine={false}
        interval="preserveStartEnd"
        minTickGap={16}
      />
      <YAxis
        tick={chartAxisTick}
        tickLine={false}
        axisLine={false}
        width={yAxisWidth}
        allowDecimals={!wholeNumbers}
        domain={[0, timeSeriesDomainMax(data)]}
        tickFormatter={formatTick}
      />
      <Tooltip
        contentStyle={chartTooltipStyle}
        formatter={(value, _name, item) => {
          const numeric = Number(value);
          const extra = (item.payload as TimeSeriesDatum | undefined)?.extra;
          return [formatValue ? formatValue(numeric, extra) : numeric, seriesName];
        }}
      />
    </>
  );

  return (
    <div style={{ height }} className="w-full min-w-0">
      <ResponsiveContainer width="100%" height="100%">
        {line ? (
          <LineChart data={data} margin={chartMarginNarrow}>
            {shared}
            <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2} dot={dot} />
          </LineChart>
        ) : (
          <AreaChart data={data} margin={chartMarginNarrow}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity={0.35} />
                <stop offset="100%" stopColor={color} stopOpacity={0.04} />
              </linearGradient>
            </defs>
            {shared}
            <Area
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={2}
              fill={`url(#${gradientId})`}
              dot={dot}
            />
          </AreaChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}
