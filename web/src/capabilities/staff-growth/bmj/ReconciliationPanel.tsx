"use client";

import { Badge, Panel, StatGrid, StatTile } from "@/foundation/ui";
import { HiOutlineArrowPath, HiOutlineChartBarSquare, HiOutlineScale } from "react-icons/hi2";
import type { DashboardSummary } from "@/capabilities/staff-growth/api";

type Report = DashboardSummary["reconciliation"];

/** What the backend's status words mean to a person. */
export function reconciliationStatus(status: string): { label: string; tone: "success" | "warning" } {
  switch (status) {
    case "ok":
      return { label: "Matches", tone: "success" };
    case "mixpanel_unconfigured":
      return { label: "Tracker off", tone: "warning" };
    case "mixpanel_error":
      return { label: "Check needed", tone: "warning" };
    default:
      return { label: status, tone: "warning" };
  }
}

/** "Do our visit numbers match?": our records against the website tracker. */
export function ReconciliationPanel({ report }: { report: Report }) {
  const status = reconciliationStatus(report.status);
  const difference =
    report.delta != null
      ? `${report.delta}${report.delta_percent != null ? ` (${report.delta_percent}%)` : ""}`
      : "-";
  return (
    <Panel
      title="Do our visit numbers match?"
      description="Uses the same dates and filters as above. Compares our records with our website tracker."
      actions={
        <>
          <Badge tone="neutral">Admin only</Badge>
          <Badge tone={status.tone}>{status.label}</Badge>
        </>
      }
    >
      <StatGrid>
        <StatTile label="Our records" value={String(report.ledger_raw_count)} icon={HiOutlineChartBarSquare} />
        <StatTile
          label="Website tracker"
          value={report.mixpanel_raw_count != null ? String(report.mixpanel_raw_count) : "-"}
          icon={HiOutlineArrowPath}
        />
        <StatTile label="Difference" value={difference} icon={HiOutlineScale} />
      </StatGrid>
    </Panel>
  );
}
