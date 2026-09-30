"use client";

import { AsyncBoundary, Panel, Row, RowList } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { listPartnerRefIds } from "@/capabilities/staff-growth/api";

/** Every link the partner sends people through. */
export function TrackingReferences({ partner }: { partner: string }) {
  const refs = useAsync((signal) => listPartnerRefIds(partner, signal), [partner]);
  return (
    <Panel
      title="Tracking references"
      description="Every link this partner sends people through."
      padding="none"
    >
      <AsyncBoundary
        state={refs}
        isEmpty={(page) => page.items.length === 0}
        empty={{
          title: "No ref ids",
          description: "This partner has no tracking links yet.",
          bare: true,
        }}
      >
        {(page) => (
          <RowList flush>
            {page.items.map((ref) => (
              <Row key={ref.ref_id}>
                <div className="min-w-0">
                  <p className="truncate text-osce-data font-medium text-ink">{ref.ref_id}</p>
                  <p className="truncate text-osce-meta text-ink-subtle">
                    {ref.exam_code} · {ref.landing_path}
                  </p>
                </div>
              </Row>
            ))}
          </RowList>
        )}
      </AsyncBoundary>
    </Panel>
  );
}
