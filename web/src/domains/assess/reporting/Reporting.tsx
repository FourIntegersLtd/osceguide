"use client";

import { AsyncBoundary, B2CEmptyState, B2CGroupedRow, B2CGroupedSection, B2CPageHeader } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { passRateLabel, readOrgReporting } from "@/domains/assess/reporting/api";

/** One row per programme, summed over every sitting held against it. */
export function Reporting({ orgSlug }: { orgSlug: string }) {
  const state = useAsync((signal) => readOrgReporting(orgSlug, signal), [orgSlug]);
  return (
    <div className="flex w-full min-w-0 flex-col gap-6">
      <B2CPageHeader
        title="Reporting"
        subtitle="Each programme across all of its sittings. The pass rate counts decisions released to candidates."
      />
      <AsyncBoundary state={state}>
        {(data) =>
          data.programmes.length === 0 ? (
            <B2CEmptyState title="No programmes yet" description="Add a programme and hold a sitting to see figures here." />
          ) : (
            <B2CGroupedSection eyebrow="Programmes">
              {data.programmes.map((row) => (
                <B2CGroupedRow
                  key={row.programme_id}
                  title={row.exam_name}
                  meta={`${row.sittings} sittings · ${row.candidates} candidates · ${passRateLabel(row)}`}
                />
              ))}
            </B2CGroupedSection>
          )
        }
      </AsyncBoundary>
    </div>
  );
}
