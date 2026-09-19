"use client";

import { AsyncBoundary } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { listOrgAuditForSupport, type AuditEntry } from "@/domains/platform/api";
import { Row, RowList, Section } from "@/domains/platform/chrome";
import { formatDay } from "@/domains/platform/support";

export function AuditSection({ slug }: { slug: string }) {
  const state = useAsync(
    (signal) => listOrgAuditForSupport(slug, { limit: 50 }, signal),
    [slug],
  );

  return (
    <Section title="Audit log" description="Recent actions inside this organisation.">
      <AsyncBoundary
        state={state}
        isEmpty={(page) => page.items.length === 0}
        empty={{ title: "No audit entries", description: "Nothing has been recorded yet." }}
      >
        {(page) => (
          <RowList>
            {page.items.map((entry) => (
              <AuditRow key={entry.id} entry={entry} />
            ))}
          </RowList>
        )}
      </AsyncBoundary>
    </Section>
  );
}

function AuditRow({ entry }: { entry: AuditEntry }) {
  return (
    <Row className="flex-col items-stretch sm:flex-row sm:items-center">
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-ink">{entry.action}</p>
        <p className="text-xs text-ink-subtle">
          {entry.actor_email ?? "Unknown actor"} · {formatDay(entry.at)}
        </p>
      </div>
      {entry.summary ? (
        <p className="max-w-md truncate text-xs text-ink-muted">{entry.summary}</p>
      ) : null}
    </Row>
  );
}
