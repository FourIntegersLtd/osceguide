"use client";

import { useState } from "react";
import { AsyncBoundary, Panel, PlatformFilterSearch } from "@/foundation/ui";
import Table, { type Column } from "@/foundation/table/Table";
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

const MUTED = "text-ink-muted";
const MONO = "font-mono text-osce-meta text-ink-muted";

function dash(value: string | null | undefined): string {
  return value ? value : "-";
}

const ARRIVAL_COLUMNS: Column<ArrivalRow>[] = [
  { header: "Visited at", key: (row) => formatUtcDateTime(row.landed_at), priority: "primary" },
  { header: "Exam", key: (row) => <span className={MUTED}>{row.exam_code ? row.exam_code.toUpperCase() : "-"}</span> },
  { header: "Campaign", key: (row) => <span className={MUTED}>{campaignLabel(row.utm_campaign)}</span> },
  { header: "Anonymous ID", key: (row) => <span className={MONO}>{dash(row.visitor_key)}</span> },
  { header: "Page", key: (row) => <span className={MUTED}>{dash(row.landing_path)}</span> },
  { header: "Visit reference", key: (row) => <span className={MONO}>{row.arrival_id}</span>, priority: "detail" },
];

const ACQUIRED_COLUMNS: Column<AcquiredUserRow>[] = [
  { header: "Signed up at", key: (row) => formatUtcDateTime(row.acquired_at), priority: "primary" },
  { header: "Account reference", key: (row) => <span className={MONO}>{row.user_id}</span> },
  { header: "Exam", key: (row) => <span className={MUTED}>{row.exam_code ? row.exam_code.toUpperCase() : "-"}</span> },
  { header: "Campaign", key: (row) => <span className={MUTED}>{campaignLabel(row.utm_campaign)}</span> },
  { header: "Anonymous ID", key: (row) => <span className={MONO}>{dash(row.visitor_key)}</span> },
];

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
          <Table<ArrivalRow> bare rows={rows} more={pages} columns={ARRIVAL_COLUMNS} idField="arrival_id" />
        )}
      </AsyncBoundary>
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
          <Table<AcquiredUserRow> bare rows={rows} more={pages} columns={ACQUIRED_COLUMNS} idField="user_id" />
        )}
      </AsyncBoundary>
    </Panel>
  );
}
