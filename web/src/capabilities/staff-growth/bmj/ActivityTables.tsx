"use client";

import { useState } from "react";
import { AsyncBoundary, LoadMore, Panel, PlatformFilterSearch } from "@/foundation/ui";
import { useCursorPages, useSearchQuery } from "@/foundation/hooks";
import { formatUtcDateTime } from "@/capabilities/attribution-dashboard/presets";
import { campaignLabel } from "@/capabilities/attribution-dashboard/viewModel";
import type { AttributionQuery } from "@/capabilities/attribution-dashboard/types";
import {
  listAcquiredUsers,
  listArrivals,
  type AcquiredUserRow,
  type ArrivalRow,
} from "@/capabilities/staff-growth/api";

const HEAD = "px-4 py-3 font-medium sm:px-6";
const CELL = "px-4 py-3 sm:px-6";
const MONO = "font-mono text-osce-meta";

function dash(value: string | null | undefined): string {
  return value ? value : "-";
}

/** "Link visits": every landing, newest first. The search is answered by the server. */
export function ArrivalsTable({
  partner,
  query,
  description,
}: {
  partner: string;
  query: AttributionQuery;
  description: string;
}) {
  const [typed, setTyped] = useState("");
  const search = useSearchQuery(typed);
  const pages = useCursorPages<ArrivalRow>(
    (cursor, signal) => listArrivals(partner, query, { search, cursor }, signal),
    [partner, query.from_date, query.to_date, query.exam_code, query.utm_campaign, search],
  );

  return (
    <Panel
      title="Link visits"
      description={description}
      padding="none"
      actions={
        <PlatformFilterSearch
          value={typed}
          onChange={setTyped}
          placeholder="Search by anonymous ID, campaign, or page…"
          aria-label="Search link visits"
        />
      }
    >
      <AsyncBoundary
        state={pages.state}
        isEmpty={(rows) => rows.length === 0}
        empty={{ title: "No link visits", description: "Nothing matches these filters.", bare: true }}
      >
        {(rows) => (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-osce-data">
              <thead className="border-b border-border text-osce-caption uppercase tracking-wide text-ink-subtle">
                <tr>
                  {["Visited at", "Exam", "Campaign", "Anonymous ID", "Page", "Visit reference"].map((title) => (
                    <th key={title} className={HEAD}>{title}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {rows.map((row) => (
                  <tr key={row.arrival_id}>
                    <td className={`${CELL} whitespace-nowrap text-ink`}>{formatUtcDateTime(row.landed_at)}</td>
                    <td className={`${CELL} text-ink-muted`}>{row.exam_code ? row.exam_code.toUpperCase() : "-"}</td>
                    <td className={`${CELL} text-ink-muted`}>{campaignLabel(row.utm_campaign)}</td>
                    <td className={`${CELL} ${MONO} text-ink-muted`}>{dash(row.visitor_key)}</td>
                    <td className={`${CELL} text-ink-muted`}>{dash(row.landing_path)}</td>
                    <td className={`${CELL} ${MONO} text-ink-muted`}>{row.arrival_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </AsyncBoundary>
      <LoadMore hasMore={pages.hasMore} busy={pages.loadingMore} onLoad={pages.loadMore} error={pages.moreError} />
    </Panel>
  );
}

/** "People who signed up": accounts credited to the partner's links. */
export function AcquiredUsersTable({
  partner,
  query,
  description,
}: {
  partner: string;
  query: AttributionQuery;
  description: string;
}) {
  const pages = useCursorPages<AcquiredUserRow>(
    (cursor, signal) => listAcquiredUsers(partner, query, cursor, signal),
    [partner, query.from_date, query.to_date, query.exam_code, query.utm_campaign],
  );

  return (
    <Panel title="People who signed up" description={description} padding="none">
      <AsyncBoundary
        state={pages.state}
        isEmpty={(rows) => rows.length === 0}
        empty={{ title: "No sign-ups", description: "Nothing matches these filters.", bare: true }}
      >
        {(rows) => (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-osce-data">
              <thead className="border-b border-border text-osce-caption uppercase tracking-wide text-ink-subtle">
                <tr>
                  {["Signed up at", "Account reference", "Exam", "Campaign", "Anonymous ID"].map((title) => (
                    <th key={title} className={HEAD}>{title}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {rows.map((row) => (
                  <tr key={row.user_id}>
                    <td className={`${CELL} whitespace-nowrap text-ink`}>{formatUtcDateTime(row.acquired_at)}</td>
                    <td className={`${CELL} ${MONO} text-ink-muted`}>{row.user_id}</td>
                    <td className={`${CELL} text-ink-muted`}>{row.exam_code ? row.exam_code.toUpperCase() : "-"}</td>
                    <td className={`${CELL} text-ink-muted`}>{campaignLabel(row.utm_campaign)}</td>
                    <td className={`${CELL} ${MONO} text-ink-muted`}>{dash(row.visitor_key)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </AsyncBoundary>
      <LoadMore hasMore={pages.hasMore} busy={pages.loadingMore} onLoad={pages.loadMore} error={pages.moreError} />
    </Panel>
  );
}
