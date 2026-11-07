"use client";

import Link from "next/link";
import { AsyncBoundary, B2CEmptyState, b2bTokens as t, cn } from "@/foundation/ui";
import { cardTitle } from "@/domains/assess/settings/SettingsCard";
import { card, row } from "@/domains/assess/ui";
import { useSurface } from "@/capabilities";
import { useAsync } from "@/foundation/hooks";
import { readOrgReporting, reportingLine } from "@/domains/assess/reporting/api";
import { boardBtn, boardPadWide } from "@/foundation/ui/boardKit";
import { useAssessWords } from "@/domains/assess/useAssessWords";
import { aOrAn } from "@/domains/assess/vocabulary";

/** One row per programme, summed over every sitting held against it. */
export function Reporting({ orgSlug }: { orgSlug: string }) {
  const w = useAssessWords();
  const { hrefFor } = useSurface();
  const state = useAsync((signal) => readOrgReporting(orgSlug, signal), [orgSlug]);
  return (
    <div className="flex min-w-0 max-w-assess-page flex-col gap-6">
      <div>
        <div className={t.assessEyebrow}>Insight</div>
        <h1 className={t.assessTitle}>Reporting</h1>
        <p className={cn(t.assessDesc, "m-0")}>{`Each exam across all of its ${w.sittings}. The pass rate counts decisions released to candidates.`}</p>
      </div>
      <AsyncBoundary state={state}>
        {(data) =>
          data.programmes.length === 0 ? (
            <B2CEmptyState title="No exams yet" description={`Set up an exam and hold ${aOrAn(w.sitting)} to see figures here.`} />
          ) : (
            <>
              <div className={card}>
                <div className={cn(row, "border-t-0")}>
                  <div className={t.assessEyebrow}>Exams</div>
                </div>
                {data.programmes.map((r) => (
                  <Link key={r.programme_id} href={hrefFor(`/sittings?exam=${encodeURIComponent(r.programme_id)}`)} className={cn(row, "hover:bg-osce-canvas")}>
                    <span className="flex-1 font-medium">
                      {r.exam_name}
                      <div className={cn(t.assessMeta, "font-normal")}>{reportingLine(r)}</div>
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
            </>
          )
        }
      </AsyncBoundary>
    </div>
  );
}
