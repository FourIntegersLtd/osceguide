"use client";

import { Alert, Badge, FactList, Panel } from "@/foundation/ui";
import Table from "@/foundation/table/Table";
import { formatBytes } from "@/domains/platform/support";
import type { Machinery } from "@/domains/platform/support/api";

type Size = NonNullable<Machinery["health"]["database_size"]>;
type Relation = Size["top_relations"][number];

const LEVEL = {
  ok: { tone: "success", text: "Within budget" },
  warning: { tone: "warning", text: "Over 60% of budget" },
  critical: { tone: "danger", text: "Over 80% of budget" },
} as const;

/**
 * How full the database is, and which tables are the weight.
 *
 * Measured live by the api, so it shows even when no background task has run.
 */
export function DatabaseSize({ size }: { size: Size | null | undefined }) {
  if (!size) {
    return (
      <Panel title="Database size">
        <Alert tone="warning">
          The database size could not be read just now. Try again in a moment.
        </Alert>
      </Panel>
    );
  }
  const level = LEVEL[size.level];
  return (
    <Panel title="Database size" actions={<Badge tone={level.tone}>{level.text}</Badge>}>
      <div className="flex flex-col gap-4">
        <FactList
          items={[
            {
              label: "Used",
              value: `${formatBytes(size.total_bytes)} of ${formatBytes(size.budget_bytes)} (${size.percent_used}%)`,
            },
          ]}
          columns={1}
        />
        {/* A sentence, not a fact: `FactList` truncates its values and this one is the forecast. */}
        <p className="text-osce-data text-ink">{size.forecast.note}</p>
        <Table<Relation>
          rows={size.top_relations}
          themeType="b2b"
          idField="name"
          title="Largest tables"
          empty={{ title: "No tables", description: "No table sizes were returned." }}
          columns={[
            { header: "Table", key: "name", priority: "primary", render: (row) => row.name },
            { header: "Size", key: "total_bytes", render: (row) => formatBytes(row.total_bytes) },
            {
              header: "Rows",
              key: "rows",
              render: (row) => (row.rows === null ? "-" : row.rows.toLocaleString("en-GB")),
            },
            {
              header: "Per row",
              key: "bytes_per_row",
              render: (row) => (row.bytes_per_row === null ? "-" : formatBytes(row.bytes_per_row)),
            },
          ]}
        />
      </div>
    </Panel>
  );
}
