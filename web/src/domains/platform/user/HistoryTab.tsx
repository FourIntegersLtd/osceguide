"use client";

import { AsyncBoundary } from "@/foundation/ui";
import Table, { type Column, type TableMore } from "@/foundation/table/Table";
import { useAsync } from "@/foundation/hooks";
import {
  listUserAudit,
  type PlatformAuditEntry,
} from "@/domains/platform/support/api";
import { humanise } from "@/foundation/format";
import { formatDetail, formatMoment } from "@/domains/platform/support";

/** What was done to this account and what it did, newest first. */
export function HistoryTab({ userId }: { userId: string }) {
  const state = useAsync(
    (signal) => listUserAudit(userId, { limit: 100 }, signal),
    [userId],
  );
  return (
    <AsyncBoundary state={state}>
      {(page) => (
        <AuditTable
          rows={page.items}
          title="History"
          description="What was done to this account and what it did, newest first."
          empty={{
            title: "No history",
            description: "Nothing has been recorded about this account.",
          }}
        />
      )}
    </AsyncBoundary>
  );
}

const auditColumns: Column<PlatformAuditEntry>[] = [
  {
    header: "Action",
    key: "action",
    priority: "primary",
    render: (entry) => (
      <div className="min-w-0">
        <p className="font-medium text-ink">{humanise(entry.action)}</p>
        <p className="truncate text-osce-meta text-ink-subtle">
          {entry.actor_email ?? "system"} · {formatMoment(entry.at)}
          {entry.org_id ? "" : " · platform"}
          {entry.target_type
            ? ` · ${humanise(entry.target_type)} ${entry.target_id ?? ""}`
            : ""}
        </p>
      </div>
    ),
  },
  {
    header: "Detail",
    key: "summary",
    render: (entry) => {
      const detail = formatDetail(entry.meta);
      return (
        <div className="max-w-md text-osce-meta text-ink-muted">
          {entry.summary ? <p className="truncate">{entry.summary}</p> : null}
          {detail ? <p className="truncate">{detail}</p> : null}
        </div>
      );
    },
  },
];

/** The audit entries as a table: this account's history and the platform-wide log both draw it. */
export function AuditTable({
  rows,
  more,
  title,
  description,
  empty,
}: {
  rows: PlatformAuditEntry[];
  more?: TableMore;
  title?: string;
  description?: string;
  empty: { title: string; description?: string };
}) {
  return (
    <Table<PlatformAuditEntry>
      rows={rows}
      more={more}
      themeType="b2b"
      idField="id"
      title={title}
      description={description}
      empty={empty}
      columns={auditColumns}
    />
  );
}
