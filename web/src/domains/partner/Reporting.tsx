"use client";

import { AsyncBoundary, b2bTokens, cn } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import { listPartnerRefIds, type TrackingPage } from "@/capabilities/staff-growth/api";
import { ReportersPanel } from "@/capabilities/staff-growth/bmj/ReportersPanel";
import { PartnerCard, PartnerHeader, Row, RowList } from "@/domains/partner/PartnerParts";

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
    <section aria-label="Reporting" className={cn(b2bTokens.assessPage, "!w-auto")}>
      <PartnerHeader title="Reporting" lead="Your tracking references, and who can see the numbers." />
      <AsyncBoundary state={refIds}>{(data) => <RefIds data={data} />}</AsyncBoundary>
      {canManageReporters ? (
        <ReportersPanel partner={partner} />
      ) : (
        <PartnerCard title="Who can read this">
          <p className={cn(b2bTokens.assessMeta, "m-0")}>
            A reporter sees these numbers and nothing else. Ask OSCE Guide staff to add someone. Reporters are added by us, not by your team.
          </p>
        </PartnerCard>
      )}
    </section>
  );
}

function RefIds({ data }: { data: TrackingPage }) {
  const items = data.items ?? [];
  return (
    <PartnerCard title="Tracking references">
      {items.length === 0 ? (
        <div data-board-hide>
          <b className="font-semibold">No references yet</b>
          <div className={b2bTokens.assessMeta}>A reference appears here the first time somebody arrives through one of your links.</div>
        </div>
      ) : (
        <RowList>
          {items.map((item, index) => (
            <Row key={item.ref_id} first={index === 0}>
              <span className="min-w-0 flex-1 basis-[260px]">
                <b className="font-semibold">{item.ref_id}</b>
                <div className={b2bTokens.assessMeta}>
                  {item.exam_code.toUpperCase()} · {item.landing_path}
                </div>
              </span>
            </Row>
          ))}
        </RowList>
      )}
    </PartnerCard>
  );
}
