"use client";

import { useAssessWords } from "@/domains/assess/useAssessWords";
import Link from "next/link";
import { useState } from "react";
import { AsyncBoundary, b2bTokens as t } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { readResultsIndex, type ResultsIndexRow } from "@/domains/assess/results/api";
import {
  attentionItems,
  filterResultsRows,
  undecided,
  resultsDate,
  type ResultsTab,
} from "@/domains/assess/results/support";
import { resultsWhere } from "@/domains/assess/sittingList";
import { useStationsToReview } from "@/domains/assess/results/StationsToReview";
import { boardCard, boardHeadRow, boardPad, boardRow, boardTab, boardTabs, boardButtonSmall } from "@/foundation/ui/boardKit";

const TABS: [ResultsTab, string][] = [
  ["needs_decision", "Needs a decision"],
  ["ready_to_release", "Ready to release"],
  ["all", "All"],
];

/** Where results work is waiting, drawn to docs/institution-overhaul/boards/Results.dc.html. */
export function ResultsIndex({ orgSlug }: { orgSlug: string }) {
  const { hrefFor } = useSurface();
  const [tab, setTab] = useState<ResultsTab>("needs_decision");
  const state = useAsync((signal) => readResultsIndex(orgSlug, signal), [orgSlug]);
  const w = useAssessWords();
  const { session } = useSession();
  const { stations } = useStationsToReview(orgSlug);
  const items = state.data
    ? attentionItems(can(session, "sign_off_results") ? (state.data.rows ?? []) : [], stations)
    : [];
  return (
    <section aria-label="Results" className={t.assessPage}>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className={t.assessEyebrow}>Run</div>
          <h1 className={t.assessTitle}>Results</h1>
          <p className={t.assessDesc}>{`Each ${w.sitting} with how far its decisions have got.`}</p>
        </div>
      </div>
      {items.length > 0 ? (
        <div className={boardPad}>
          <h2 className="text-base font-semibold leading-normal">Needs your attention</h2>
          {items.map((item) => (
            <Link
              key={item.key}
              href={hrefFor(item.path)}
              className="flex flex-wrap items-center gap-4 py-2.5 text-assess-label text-osce-ink-900"
            >
              <span className="flex-1">{item.text}</span>
              <span className={boardButtonSmall}>{item.action}</span>
            </Link>
          ))}
        </div>
      ) : null}
      <div role="tablist" aria-label="Filter results" className={boardTabs}>
        {TABS.map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            className={boardTab(tab === id)}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </div>
      <AsyncBoundary
        state={state}
        isEmpty={(data) => (data.rows ?? []).length === 0}
        empty={{
          title: "No results yet.",
          description: `Results appear here once ${w.sitting === "sitting" ? "a sitting" : "an assessment"} has ${w.trainees}.`,
        }}
      >
        {(data) => {
          const rows = filterResultsRows(data.rows ?? [], tab);
          return (
            <>
              {data.truncated ? (
                <p role="status" className={t.assessMeta}>
                  Showing the {(data.rows ?? []).length} most recent {w.sittings}.
                </p>
              ) : null}
              {rows.length === 0 ? (
                <div className={boardPad}>
                  <h2 className="text-base font-semibold leading-normal">Nothing here.</h2>
                  <p className={`m-0 ${t.assessMeta}`}>{`No ${w.sitting} matches this tab.`}</p>
                </div>
              ) : (
                <div className={`${boardCard} overflow-hidden`}>
                  <div className={boardHeadRow}>
                    <span className="flex-[1_1_200px]">{w.Sitting}</span>
                    <span className="w-20">Date</span>
                    <span className="w-[100px]">Kind</span>
                    <span className="w-[70px]">Candidates</span>
                    <span className="w-20">Not decided</span>
                    <span className="w-[50px]">Draft</span>
                    <span className="w-20">Signed off</span>
                    <span className="w-[70px]">Released</span>
                    <span className="w-[170px]">Where it is</span>
                  </div>
                  {rows.map((row) => (
                    <ResultsRow key={row.sitting_id} row={row} href={hrefFor(`/sittings/${row.sitting_id}/results`)} />
                  ))}
                </div>
              )}
            </>
          );
        }}
      </AsyncBoundary>
    </section>
  );
}

function ResultsRow({ row, href }: { row: ResultsIndexRow; href: string }) {
  // A training sitting records no decisions, so its decision columns read as dashes.
  const decides = row.mode === "exam";
  const num = (value: number) => (decides ? value : "-");
  return (
    <Link href={href} className={`${boardRow} hover:bg-osce-surface-inset`}>
      <span className="flex-[1_1_200px] font-medium">{row.name}</span>
      <span className={`w-20 ${t.assessMeta}`}>{resultsDate(row.scheduled_for)}</span>
      <span className={`w-[100px] ${t.assessMeta}`}>{decides ? "Formal exam" : "Training"}</span>
      <span className="w-[70px]">{row.candidates}</span>
      <span className="w-20">{num(undecided(row))}</span>
      <span className="w-[50px]">{num(row.draft)}</span>
      <span className="w-20">{num(row.signed_off)}</span>
      <span className="w-[70px]">{num(row.released)}</span>
      <span className="w-[170px] font-medium">{resultsWhere(row)}</span>
    </Link>
  );
}
