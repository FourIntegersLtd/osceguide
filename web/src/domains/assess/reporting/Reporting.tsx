"use client";

import Link from "next/link";
import { AsyncBoundary, B2CEmptyState, B2CGroupedRow, B2CGroupedSection, B2CPageHeader, b2bTokens } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { useAsync } from "@/foundation/hooks";
import { passRateLabel, readOrgReporting } from "@/domains/assess/reporting/api";

/** One row per programme, summed over every sitting held against it. */
export function Reporting({ orgSlug }: { orgSlug: string }) {
  const { hrefFor } = useSurface();
  const state = useAsync((signal) => readOrgReporting(orgSlug, signal), [orgSlug]);
  return (
    <div className="flex w-full min-w-0 flex-col gap-6">
      <B2CPageHeader
        title="Reporting"
        subtitle="Each exam across all of its sittings. The pass rate counts decisions released to candidates."
      />
      <AsyncBoundary state={state}>
        {(data) =>
          data.programmes.length === 0 ? (
            <B2CEmptyState title="No exams yet" description="Set up an exam and hold a sitting to see figures here." />
          ) : (
            <>
            <B2CGroupedSection eyebrow="Exams">
              {data.programmes.map((row) => (
                <B2CGroupedRow
                  key={row.programme_id}
                  title={row.exam_name}
                  meta={`${row.sittings} sittings · ${row.candidates} candidates · ${passRateLabel(row)}`}
                />
              ))}
            </B2CGroupedSection>
            <B2CGroupedSection eyebrow="Per-sitting reports">
              <B2CGroupedRow
                title="Each sitting's report, CSV and readout live on its Results page."
                meta={
                  <Link href={hrefFor("/results")} className={b2bTokens.b2bLink}>
                    Open results
                  </Link>
                }
              />
            </B2CGroupedSection>
            </>
          )
        }
      </AsyncBoundary>
    </div>
  );
}
