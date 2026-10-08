"use client";

import { AsyncBoundary, EmptyState, B2CPageHeader, Panel } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import { listPartnerRefIds, type TrackingPage } from "@/capabilities/staff-growth/api";
import { ReportersPanel } from "@/capabilities/staff-growth/bmj/ReportersPanel";

/**
 * The links a partner publishes, and who may read the numbers.
 *
 * Each tracking reference is a separate campaign — a journal article, a
 * newsletter, a conference — so they are listed rather than summed. The funnel
 * on the overview is the sum; this is where a partner sees which of their
 * placements actually worked.
 */
export function PartnerReporting({ partner }: { partner: string }) {
  const { session } = useSession();
  const refIds = useAsync((signal) => listPartnerRefIds(partner, signal), [partner]);
  /*
   * A reporter is appointed and removed by OSCE Guide staff, not by the partner —
   * the backend routes are platform-admin only ("partners do not appoint their
   * own reporters"). Staff see the list with add and remove; a partner team
   * member sees where to ask. This reads the permission the backend checks.
   */
  const canManageReporters = can(session, "administer_platform");

  return (
    <div className="flex flex-col gap-6">
      <B2CPageHeader
        title="Reporting"
        subtitle="Your tracking references, and who can see the numbers."
      />
      <AsyncBoundary state={refIds}>{(data) => <RefIds data={data} />}</AsyncBoundary>
      {canManageReporters ? (
        <ReportersPanel partner={partner} />
      ) : (
        <Panel title="Who can read this">
          <p className="text-sm text-ink-muted">
            A reporter sees these numbers and nothing else. Ask OSCE Guide staff to add someone. Reporters are added by us, not by your team.
          </p>
        </Panel>
      )}
    </div>
  );
}

function RefIds({ data }: { data: TrackingPage }) {
  const items = data.items ?? [];

  return (
    <Panel title="Tracking references">
      {items.length === 0 ? (
        <EmptyState
          title="No references yet"
          description="A reference appears here the first time somebody arrives through one of your links."
        />
      ) : (
        <ul className="divide-y divide-border">
          {items.map((item) => (
            <li key={item.ref_id} className="flex flex-wrap items-center justify-between gap-3 py-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-ink">{item.ref_id}</p>
                <p className="truncate text-xs text-ink-subtle">
                  {item.exam_code.toUpperCase()} · {item.landing_path}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
