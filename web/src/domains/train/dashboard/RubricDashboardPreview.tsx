"use client";

import { useMemo } from "react";
import type { RubricDashboardPreviewProps } from "@/capabilities/authoring/rubrics/dashboardSlot";
import { DomainPerformanceCard } from "@/domains/train/dashboard/DomainPerformanceCard";
import { TrendCard } from "@/domains/train/dashboard/TrendCard";
import { dashboardView } from "@/domains/train/dashboard/dashboardView";
import { previewPerformance } from "@/domains/train/dashboard/previewPerformance";

/**
 * The two dashboard charts a draft rubric would give a learner, drawn by the
 * same cards and the same `dashboardView` the real dashboard uses. Mounted
 * into the rubric builder by its route (see `dashboardSlot.ts`).
 */
export function RubricDashboardPreview(props: RubricDashboardPreviewProps) {
  const view = useMemo(() => dashboardView(previewPerformance(props, new Date())), [props]);
  return (
    <div className="space-y-4">
      <p className="text-osce-meta text-osce-ink-500">
        Your dashboard, drawn from one sample result, so the trend only shows the axes and pass line.
      </p>
      <DomainPerformanceCard chart={view.domainChart} loading={false} />
      <TrendCard scale={view.trend} loading={false} />
    </div>
  );
}
