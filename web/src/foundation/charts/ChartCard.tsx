"use client";

import type { ReactNode } from "react";
import {
  b2cCard,
  b2cDashboardChartWell,
  b2cSectionTitle,
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
  // Canvas card: header 18px 20px 4px with a t3 title, body 12px 20px 20px.
  const shellClass = flat ? "min-w-0" : `${b2cCard} overflow-hidden`;
  const pad = flat ? "" : "px-5";

  return (
    <div className={`${shellClass} min-w-0 ${className}`}>
      <div className={`flex min-w-0 items-start justify-between gap-4 ${flat ? "pb-3" : "pb-1 pt-[18px]"} ${pad}`}>
        <div className="min-w-0 flex-1">
          <h2 className={b2cSectionTitle}>{title}</h2>
          {subtitle ? <p className="mt-0.5 text-osce-meta text-b2c-text-muted">{subtitle}</p> : null}
        </div>
        {action ? <div className="flex shrink-0 gap-2">{action}</div> : null}
      </div>
      <div className={flat ? "" : "px-5 pb-5 pt-3"}>
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
    </div>
  );
}
