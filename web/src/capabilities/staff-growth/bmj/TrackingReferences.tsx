"use client";

import { AsyncBoundary } from "@/foundation/ui";
import Table, { type Column } from "@/foundation/table/Table";
import { useAsync } from "@/foundation/hooks";
import { listPartnerRefIds } from "@/capabilities/staff-growth/api";

type Ref = { ref_id: string; exam_code: string; landing_path: string };

const columns: Column<Ref>[] = [
  { header: "Ref id", key: "ref_id", priority: "primary", render: (ref) => <span className="font-medium text-ink">{ref.ref_id}</span> },
  { header: "Exam", key: "exam_code" },
  { header: "Landing path", key: "landing_path", className: "truncate" },
];

/** Every link the partner sends people through. */
export function TrackingReferences({ partner }: { partner: string }) {
  const refs = useAsync((signal) => listPartnerRefIds(partner, signal), [partner]);
  return (
    <AsyncBoundary state={refs}>
      {(page) => (
        <Table<Ref>
          rows={page.items}
          themeType="b2b"
          idField="ref_id"
          title="Tracking references"
          description="Every link this partner sends people through."
          empty={{ title: "No ref ids", description: "This partner has no tracking links yet." }}
          columns={columns}
        />
      )}
    </AsyncBoundary>
  );
}
