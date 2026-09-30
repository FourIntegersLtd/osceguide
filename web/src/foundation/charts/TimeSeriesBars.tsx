"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
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

/** One bucket on a time axis: the label already formatted for the axis. */
export interface TimeSeriesDatum {
  label: string;
  value: number;
  /** A second number the tooltip can quote beside the value. */
  extra?: number;
}

export interface TimeSeriesProps {
  data: TimeSeriesDatum[];
  color: string;
  /** What the tooltip calls the series ("Link visits"). */
  seriesName: string;
  /** How a value reads in the tooltip. Defaults to the plain number. */
  formatValue?: (value: number, extra?: number) => string;
  /** How a tick reads on the y axis. Defaults to the plain number. */
  formatTick?: (value: number) => string;
  /** Whole counts only (visits) versus money, which may need decimals. */
  wholeNumbers?: boolean;
  yAxisWidth?: number;
  height?: number;
}

/** Headroom above the tallest value, so a bar never touches the top of the plot. */
export function timeSeriesDomainMax(data: TimeSeriesDatum[]): number {
  const largest = data.reduce((max, point) => Math.max(max, point.value), 0);
  return largest * 1.1 || 1;
}

/**
 * Counts (or money) per day, week or month as bars.
 *
 * Generic on purpose: the partner's visits, the partner's fee and any later
 * per-bucket measure draw through this one chart, so they stay on the same
 * grid, ticks and tooltip.
 */
export default function TimeSeriesBars({
  data,
  color,
  seriesName,
  formatValue,
  formatTick,
  wholeNumbers = true,
  yAxisWidth = 36,
  height = CHART_HEIGHT,
}: TimeSeriesProps) {
  return (
    <div style={{ height }} className="w-full min-w-0">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={chartMarginNarrow}>
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
            cursor={{ fill: chartColors.grid }}
            formatter={(value, _name, item) => {
              const numeric = Number(value);
              const extra = (item.payload as TimeSeriesDatum | undefined)?.extra;
              return [formatValue ? formatValue(numeric, extra) : numeric, seriesName];
            }}
          />
          <Bar dataKey="value" fill={color} radius={[6, 6, 0, 0]} maxBarSize={36} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
