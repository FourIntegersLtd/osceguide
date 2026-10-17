"use client";

import { AsyncBoundary } from "@/foundation/ui";
import Table, { type Column } from "@/foundation/table/Table";
import { useCursorPages } from "@/foundation/hooks";
import {
  listOrgAuditForSupport,
  type AuditEntry,
} from "@/domains/platform/api";
import { humanise } from "@/foundation/format";
import { formatDay } from "@/domains/platform/support";

const columns: Column<AuditEntry>[] = [
  {
    header: "Action",
    key: "action",
    priority: "primary",
    render: (entry) => (
      <div className="min-w-0">
        <p className="font-medium text-ink">{humanise(entry.action)}</p>
        <p className="text-osce-meta text-ink-subtle">
          {entry.actor_email ?? "Unknown actor"} · {formatDay(entry.at)}
        </p>
      </div>
    ),
  },
  {
    header: "Detail",
    key: "summary",
    render: (entry) =>
      entry.summary ? (
        <p className="max-w-md truncate text-osce-meta text-ink-muted">{entry.summary}</p>
      ) : null,
  },
];

export function AuditSection({ slug }: { slug: string }) {
  const pages = useCursorPages(
    (cursor, signal) => listOrgAuditForSupport(slug, { limit: 50, cursor }, signal),
    [slug],
  );

  return (
    <AsyncBoundary state={pages.state}>
      {(items) => (
        <Table<AuditEntry>
          rows={items}
          more={pages}
          themeType="b2b"
          idField="id"
          title="Audit log"
          description="Recent actions inside this organisation."
          empty={{ title: "No audit entries", description: "Nothing has been recorded yet." }}
          columns={columns}
        />
      )}
    </AsyncBoundary>
  );
}
