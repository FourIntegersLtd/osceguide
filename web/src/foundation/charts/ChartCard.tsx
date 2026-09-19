"use client";

import type { ReactNode } from "react";
import { B2CMonoEyebrow } from "@/foundation/ui/B2CMonoEyebrow";
import {
  b2cCardPadding,
  b2cDashboardCard,
  b2cDashboardChartWell,
} from "@/foundation/ui/productTokens";

interface ChartCardProps {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  loading?: boolean;
  /** When false, children render without the muted chart well (lists, trends). */
  inset?: boolean;
  /** Title on canvas — no outer card border/shadow (chart well keeps its own border). */
  flat?: boolean;
  children: ReactNode;
  className?: string;
}

export default function ChartCard({
  title,
  subtitle,
  action,
  loading = false,
  inset = true,
  flat = false,
  children,
  className = "",
}: ChartCardProps) {
  const shellClass = flat
    ? "min-w-0"
    : `${b2cDashboardCard} ${b2cCardPadding} min-h-[320px]`;

  return (
    <div className={`${shellClass} min-w-0 ${className}`}>
      <div className="mb-5 flex min-w-0 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1 overflow-visible">
          <B2CMonoEyebrow className="leading-normal">{title}</B2CMonoEyebrow>
          {subtitle ? (
            <p className="mt-2 text-osce-meta text-b2c-text-secondary">
              {subtitle}
            </p>
          ) : null}
        </div>
        {action ? <div className="min-w-0 w-full sm:w-auto sm:shrink-0">{action}</div> : null}
      </div>
      {loading ? (
        <div
          className="h-[220px] animate-pulse rounded-lg border border-b2c-border bg-b2c-surface-muted"
          aria-label="Loading chart"
          role="status"
        />
      ) : inset ? (
        <div className={b2cDashboardChartWell}>{children}</div>
      ) : (
        children
      )}
    </div>
  );
}
