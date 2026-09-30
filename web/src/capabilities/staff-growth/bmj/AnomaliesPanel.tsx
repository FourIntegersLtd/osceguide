"use client";

import { HiOutlineExclamationTriangle, HiOutlineShieldExclamation, HiOutlineInformationCircle } from "react-icons/hi2";
import { Badge, Panel } from "@/foundation/ui";
import type { DashboardSummary } from "@/capabilities/staff-growth/api";

type Report = DashboardSummary["anomalies"];

const SEVERITY = {
  critical: { Icon: HiOutlineShieldExclamation, label: "Critical", tone: "danger", row: "bg-danger-subtle text-danger" },
  warning: { Icon: HiOutlineExclamationTriangle, label: "Warning", tone: "warning", row: "bg-warning-subtle text-warning" },
  info: { Icon: HiOutlineInformationCircle, label: "Info", tone: "neutral", row: "bg-canvas text-ink" },
} as const;

function severityOf(severity: string) {
  return severity === "critical" || severity === "warning" ? SEVERITY[severity] : SEVERITY.info;
}

/** "Do the numbers add up?": the automatic checks, with a pill that counts the flags. */
export function AnomaliesPanel({ report }: { report: Report }) {
  const flagged = report.status === "flagged" && report.count > 0;
  return (
    <Panel
      title="Do the numbers add up?"
      description="Automatic checks when something looks out of place."
      actions={
        <>
        <Badge tone="neutral">Admin only</Badge>
        <Badge tone={flagged ? "warning" : "success"}>
          {flagged ? `${report.count} flag${report.count === 1 ? "" : "s"}` : "All clear"}
        </Badge>
        </>
      }
    >
      {flagged ? (
        <ul className="space-y-3">
          {report.items.map((item) => {
            const severity = severityOf(item.severity);
            return (
              <li key={`${item.code}-${item.title}`} className={`rounded-osce-lg px-4 py-3 ${severity.row}`}>
                <div className="flex items-start gap-3">
                  <severity.Icon className="mt-0.5 h-5 w-5 shrink-0" aria-hidden />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-osce-data font-medium">{item.title}</p>
                      <Badge tone={severity.tone}>{severity.label}</Badge>
                      {item.metric ? <span className="text-osce-caption">{item.metric}</span> : null}
                    </div>
                    <p className="mt-1 text-osce-meta text-ink-muted">{item.detail}</p>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="text-osce-meta text-ink-subtle">Nothing looks out of place for the current filters.</p>
      )}
    </Panel>
  );
}
