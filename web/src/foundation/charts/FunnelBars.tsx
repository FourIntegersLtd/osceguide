"use client";

import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  chartAxisTick,
  chartColors,
  chartTooltipStyle,
} from "@/foundation/charts/chartTheme";

export interface FunnelBarDatum {
  label: string;
  /** Null is a step the server could not count; it draws as a faint stub. */
  count: number | null;
  color: string;
  /** How the tooltip captions this step ("Signed up · 12% of visits"). */
  caption: string;
}

/** Steps as horizontal bars, widest first, one colour per step. */
export default function FunnelBars({
  data,
  height,
}: {
  data: FunnelBarDatum[];
  height: number;
}) {
  const plotted = data.map((datum) => ({ ...datum, plotted: datum.count ?? 0 }));
  return (
    <div style={{ height }} className="w-full min-w-0">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={plotted}
          layout="vertical"
          margin={{ top: 4, right: 16, left: 8, bottom: 0 }}
        >
          <XAxis type="number" hide allowDecimals={false} />
          <YAxis
            type="category"
            dataKey="label"
            tick={chartAxisTick}
            tickLine={false}
            axisLine={false}
            width={72}
          />
          <Tooltip
            contentStyle={chartTooltipStyle}
            cursor={{ fill: chartColors.grid }}
            formatter={(value, _name, item) =>
              (item.payload as { count: number | null }).count === null
                ? ["Not tracked yet", "Count"]
                : [Number(value), "People"]
            }
            labelFormatter={(_label, payload) =>
              (payload[0]?.payload as { caption?: string } | undefined)?.caption ?? ""
            }
          />
          <Bar dataKey="plotted" radius={[0, 6, 6, 0]} maxBarSize={28}>
            {plotted.map((datum) => (
              <Cell
                key={datum.label}
                fill={datum.count === null ? chartColors.slate : datum.color}
                fillOpacity={datum.count === null ? 0.35 : 1}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
