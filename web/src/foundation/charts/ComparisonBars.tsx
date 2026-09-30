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
import {
  CHART_HEIGHT,
  chartAxisTick,
  chartColors,
  chartMarginNarrow,
  chartTooltipStyle,
} from "@/foundation/charts/chartTheme";

export interface ComparisonBarDatum {
  label: string;
  value: number;
  color: string;
}

interface ComparisonBarsProps {
  data: ComparisonBarDatum[];
  /** What the tooltip calls the measure ("Amount"). */
  seriesName: string;
  formatValue: (value: number) => string;
  formatTick?: (value: number) => string;
  /** Tilt the x labels, for long category names (plans). */
  angleLabels?: boolean;
  yAxisWidth?: number;
  height?: number;
}

/**
 * A handful of named bars, each its own colour: spend against money in,
 * revenue by plan. Bars may be negative (money left over), so the y axis is not
 * pinned at zero the way the time-series charts' is.
 */
export default function ComparisonBars({
  data,
  seriesName,
  formatValue,
  formatTick,
  angleLabels = false,
  yAxisWidth = 52,
  height = CHART_HEIGHT,
}: ComparisonBarsProps) {
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
            interval={0}
            angle={angleLabels ? -20 : 0}
            textAnchor={angleLabels ? "end" : "middle"}
            height={angleLabels ? 52 : 30}
          />
          <YAxis
            tick={chartAxisTick}
            tickLine={false}
            axisLine={false}
            width={yAxisWidth}
            tickFormatter={formatTick}
          />
          <Tooltip
            contentStyle={chartTooltipStyle}
            cursor={{ fill: chartColors.grid }}
            formatter={(value) => [formatValue(Number(value)), seriesName]}
          />
          <Bar dataKey="value" radius={[6, 6, 0, 0]} maxBarSize={72}>
            {data.map((datum) => (
              <Cell key={datum.label} fill={datum.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
