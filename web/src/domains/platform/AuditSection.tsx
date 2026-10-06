"use client";

import { AsyncBoundary, Panel, Row, RowList } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import {
  listOrgAuditForSupport,
  type AuditEntry,
} from "@/domains/platform/api";
import { formatDay, humanise } from "@/domains/platform/support";

export function AuditSection({ slug }: { slug: string }) {
  const state = useAsync(
    (signal) => listOrgAuditForSupport(slug, { limit: 50 }, signal),
    [slug],
  );

  return (
    <Panel
      title="Audit log"
      description="Recent actions inside this organisation."
      padding="none"
    >
      <AsyncBoundary
        state={state}
        isEmpty={(page) => page.items.length === 0}
        empty={{
          title: "No audit entries",
          description: "Nothing has been recorded yet.",
          bare: true,
        }}
      >
        {(page) => (
          <RowList flush>
            {page.items.map((entry) => (
              <AuditRow key={entry.id} entry={entry} />
            ))}
          </RowList>
        )}
      </AsyncBoundary>
    </Panel>
  );
}

function AuditRow({ entry }: { entry: AuditEntry }) {
  return (
    <Row className="flex-col items-stretch sm:flex-row sm:items-center">
      <div className="min-w-0 flex-1">
        <p className="text-osce-data font-medium text-ink">{humanise(entry.action)}</p>
        <p className="text-osce-meta text-ink-subtle">
          {entry.actor_email ?? "Unknown actor"} · {formatDay(entry.at)}
        </p>
      </div>
      {entry.summary ? (
        <p className="max-w-md truncate text-osce-meta text-ink-muted">
          {entry.summary}
        </p>
      ) : null}
    </Row>
  );
}
