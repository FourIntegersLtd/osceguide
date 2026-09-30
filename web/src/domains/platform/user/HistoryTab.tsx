"use client";

import { AsyncBoundary, Panel, Row, RowList } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import {
  listUserAudit,
  type PlatformAuditEntry,
} from "@/domains/platform/support/api";
import { formatMoment } from "@/domains/platform/support";

/** What was done to this account and what it did, newest first. */
export function HistoryTab({ userId }: { userId: string }) {
  const state = useAsync(
    (signal) => listUserAudit(userId, { limit: 100 }, signal),
    [userId],
  );
  return (
    <Panel
      title="History"
      description="What was done to this account and what it did, newest first."
      padding="none"
    >
      <AsyncBoundary
        state={state}
        isEmpty={(page) => page.items.length === 0}
        empty={{
          title: "No history",
          description: "Nothing has been recorded about this account.",
          bare: true,
        }}
      >
        {(page) => (
          <RowList flush>
            {page.items.map((entry) => (
              <PlatformAuditRow key={entry.id} entry={entry} />
            ))}
          </RowList>
        )}
      </AsyncBoundary>
    </Panel>
  );
}

export function PlatformAuditRow({ entry }: { entry: PlatformAuditEntry }) {
  const meta = entry.meta
    ? Object.entries(entry.meta).filter(
        ([, value]) => value !== null && value !== "",
      )
    : [];
  return (
    <Row className="flex-col items-stretch sm:flex-row sm:items-center">
      <div className="min-w-0 flex-1">
        <p className="text-osce-data font-medium text-ink">{entry.action}</p>
        <p className="truncate text-osce-meta text-ink-subtle">
          {entry.actor_email ?? "system"} · {formatMoment(entry.at)}
          {entry.org_id ? "" : " · platform"}
          {entry.target_type
            ? ` · ${entry.target_type} ${entry.target_id ?? ""}`
            : ""}
        </p>
      </div>
      <div className="max-w-md text-osce-meta text-ink-muted">
        {entry.summary ? <p className="truncate">{entry.summary}</p> : null}
        {meta.length > 0 ? (
          <p className="truncate">
            {meta.map(([key, value]) => `${key}=${String(value)}`).join(" · ")}
          </p>
        ) : null}
      </div>
    </Row>
  );
}
