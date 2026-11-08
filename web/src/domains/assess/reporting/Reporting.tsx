"use client";

import Link from "next/link";
import { AsyncBoundary, B2CEmptyState, b2bTokens as t, cn } from "@/foundation/ui";
import { cardTitle } from "@/domains/assess/settings/SettingsCard";
import { card, row } from "@/domains/assess/ui";
import { useSurface } from "@/capabilities";
import { useAsync } from "@/foundation/hooks";
import { useAssessWords } from "@/capabilities/assess-words";
import { aOrAn } from "@/capabilities/assess-words/vocabulary";
import { assessorsTile, HIRE_REPORTING, readOrgReporting, reportingLine, reportTiles, STATION_TABLE_HEADS, stationCells } from "@/domains/assess/reporting/api";
import { boardBtn, boardPadWide } from "@/foundation/ui/boardKit";

/** One row per programme, summed over every sitting held against it. */
export function Reporting({ orgSlug }: { orgSlug: string }) {
  const { hrefFor } = useSurface();
  const w = useAssessWords();
  const state = useAsync((signal) => readOrgReporting(orgSlug, signal), [orgSlug]);
  return (
    <div className="flex min-w-0 max-w-assess-page flex-col gap-6">
      <div>
        <div className={t.assessEyebrow}>Insight</div>
        <h1 className={t.assessTitle}>Reporting</h1>
        <p className={cn(t.assessDesc, "m-0")}>
          {w.hiring ? HIRE_REPORTING.description : `Each exam across all of its ${w.sittings}. The pass rate counts decisions released to candidates.`}
        </p>
      </div>
      <AsyncBoundary state={state}>
        {(data) =>
          data.programmes.length === 0 ? (
            <B2CEmptyState
              title={w.hiring ? HIRE_REPORTING.emptyTitle : "No exams yet"}
              description={w.hiring ? HIRE_REPORTING.emptyBody : `Set up an exam and hold ${aOrAn(w.sitting)} to see figures here.`}
              action={
                w.hiring ? (
                  <Link href={hrefFor("/results")} className={boardBtn("primary")}>
                    {HIRE_REPORTING.emptyLink}
                  </Link>
                ) : undefined
              }
            />
          ) : (
            <>
              {w.hiring ? (
                <div className="grid grid-cols-2 gap-3 min-[901px]:grid-cols-4">
                  {[...reportTiles(data.programmes, w), assessorsTile(data.assessors_marking)].map((tile) => (
                    <div key={tile.label} className={boardPadWide}>
                      <div className={t.assessMeta}>{tile.label}</div>
                      <div className="text-assess-h2 font-semibold">{tile.value}</div>
                    </div>
                  ))}
                </div>
              ) : null}
              {w.hiring && data.stations.length > 0 ? (
                <div className={card} role="table" aria-label="Stations">
                  <div role="row" className={cn(row, "border-t-0", t.assessEyebrow)}>
                    {STATION_TABLE_HEADS.map((head, at) => (
                      <span key={head} role="columnheader" className={at === 0 ? "flex-1" : "w-44"}>
                        {head}
                      </span>
                    ))}
                  </div>
                  {data.stations.map((station) => (
                    <div key={station.station_title} role="row" className={row}>
                      {stationCells(station).map((cell, at) => (
                        <span key={at} role="cell" className={at === 0 ? "flex-1 font-medium" : "w-44"}>
                          {cell}
                        </span>
                      ))}
                    </div>
                  ))}
                </div>
              ) : null}
              <div className={card}>
                <div className={cn(row, "border-t-0")}>
                  <div className={t.assessEyebrow}>Exams</div>
                </div>
                {data.programmes.map((r) => (
                  <Link key={r.programme_id} href={hrefFor(`/sittings?exam=${encodeURIComponent(r.programme_id)}`)} className={cn(row, "hover:bg-osce-canvas")}>
                    <span className="flex-1 font-medium">
                      {r.exam_name}
                      <div className={cn(t.assessMeta, "font-normal")}>{reportingLine(r, w)}</div>
                    </span>
                    <span className={t.assessMeta}>›</span>
                  </Link>
                ))}
              </div>
              <section className={boardPadWide}>
                <h2 className={cardTitle}>{`Per-${w.sitting} reports`}</h2>
                <div className={t.assessMeta}>{`Each ${w.sitting}'s report, CSV and readout live on its Results page.`}</div>
                <Link href={hrefFor("/results")} className={cn(boardBtn("default"), "self-start")}>
                  Open results
                </Link>
              </section>
              {w.hiring ? <p className={t.assessMeta}>{HIRE_REPORTING.note}</p> : null}
            </>
          )
        }
      </AsyncBoundary>
    </div>
  );
}
