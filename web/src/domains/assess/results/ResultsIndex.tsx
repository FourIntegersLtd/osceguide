"use client";

import { useAssessWords } from "@/domains/assess/useAssessWords";
import Link from "next/link";
import { useMemo, useState } from "react";
import { LuClipboardCheck } from "react-icons/lu";
import {
  AsyncBoundary,
  B2CGroupedRowLink,
  B2CGroupedSection,
  B2CPageHeader,
  B2CSegmentedTabs,
  Badge,
} from "@/foundation/ui";
import Table, { type Column } from "@/foundation/table/Table";
import { b2cTableCellText } from "@/foundation/ui/productTokens";
import { useAsync } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import {
  readResultsIndex,
  type ResultsIndexRow,
} from "@/domains/assess/results/api";
import {
  attentionItems,
  filterResultsRows,
  type AttentionItem,
  type ResultsTab,
} from "@/domains/assess/results/support";
import { useStationsToReview } from "@/domains/assess/results/StationsToReview";

const cell = `${b2cTableCellText} text-b2b-graphite`;

const count = (
  key: "candidates" | "not_decided" | "draft" | "signed_off" | "released",
  header: string,
): Column<ResultsIndexRow> => ({
  header,
  key,
  render: (row: ResultsIndexRow) => <span className={cell}>{row[key]}</span>,
});

const columnsFor = (
  hrefFor: (path: string) => string,
  sittingWord: string,
): Column<ResultsIndexRow>[] => [
  {
    header: sittingWord,
    key: "name",
    priority: "primary",
    render: (row: ResultsIndexRow) => (
      <Link
        href={hrefFor(`/sittings/${row.sitting_id}/results`)}
        className={`${b2cTableCellText} font-medium text-osce-ink-900 hover:underline`}
      >
        {row.name}
      </Link>
    ),
  },
  {
    header: "Date",
    key: "scheduled_for",
    render: (row: ResultsIndexRow) => (
      <span className={cell}>
        {row.scheduled_for
          ? new Date(row.scheduled_for).toLocaleDateString()
          : "Not scheduled"}
      </span>
    ),
  },
  {
    header: "Kind",
    key: "mode",
    render: (row: ResultsIndexRow) => (
      <span className={cell}>{row.mode === "exam" ? "Formal exam" : "Training"}</span>
    ),
  },
  count("candidates", "Candidates"),
  count("not_decided", "Not decided"),
  count("draft", "Draft"),
  count("signed_off", "Signed off"),
  count("released", "Released"),
];

/** Where results work is waiting: every sitting with its candidates by decision stage. */
export function ResultsIndex({ orgSlug }: { orgSlug: string }) {
  const { hrefFor } = useSurface();
  const [tab, setTab] = useState<ResultsTab>("needs_decision");
  const state = useAsync(
    (signal) => readResultsIndex(orgSlug, signal),
    [orgSlug],
  );
  const w = useAssessWords();
  const { session } = useSession();
  const { stations } = useStationsToReview(orgSlug);
  const columns = useMemo(
    () => columnsFor(hrefFor, w.Sitting),
    [hrefFor, w.Sitting],
  );
  return (
    <div className="flex flex-col gap-6">
      <B2CPageHeader
        title="Results"
        subtitle={`Each ${w.sitting} with how far its decisions have got.`}
      />
      {state.data ? (
        <NeedsAttention
          items={attentionItems(
            can(session, "sign_off_results") ? (state.data.rows ?? []) : [],
            stations,
          )}
        />
      ) : null}
      <B2CSegmentedTabs<ResultsTab>
        aria-label="Filter results"
        compact
        value={tab}
        onChange={setTab}
        items={[
          { id: "needs_decision", label: "Needs a decision" },
          { id: "ready_to_release", label: "Ready to release" },
          { id: "all", label: "All" },
        ]}
      />
      <AsyncBoundary
        state={state}
        isEmpty={(data) => (data.rows ?? []).length === 0}
        empty={{
          title: "No results yet.",
          description: `Results appear here once ${w.sitting === "sitting" ? "a sitting" : "an assessment"} has ${w.trainees}.`,
        }}
      >
        {(data) => (
          <>
            {data.truncated ? (
              <p role="status" className="mb-3 text-sm text-b2b-graphite">
                Showing the {(data.rows ?? []).length} most recent {w.sittings}.
              </p>
            ) : null}
            <Table<ResultsIndexRow>
              rows={filterResultsRows(data.rows ?? [], tab)}
              themeType="b2b"
              columns={columns}
              idField="sitting_id"
              empty={{ title: "Nothing here.", description: `No ${w.sitting} matches this tab.` }}
            />
          </>
        )}
      </AsyncBoundary>
    </div>
  );
}

/** "Needs your attention": what is waiting on this person, before the full list. */
function NeedsAttention({ items }: { items: AttentionItem[] }) {
  const { hrefFor } = useSurface();
  if (items.length === 0) return null;
  return (
    <B2CGroupedSection eyebrow="Needs your attention">
      {items.map((item) => (
        <B2CGroupedRowLink
          key={item.key}
          href={hrefFor(item.path)}
          icon={LuClipboardCheck}
          title={item.text}
          trailing={<Badge variant="info">{item.action}</Badge>}
        />
      ))}
    </B2CGroupedSection>
  );
}
