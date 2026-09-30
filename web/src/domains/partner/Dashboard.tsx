"use client";

import { useMemo } from "react";
import { AsyncBoundary, B2CSegmentedTabs, PageHeader } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useAttributionState } from "@/foundation/attribution/useAttributionFilters";
import { getDashboardCopy } from "@/foundation/attribution/copy";
import { filterScope, tabsForMode } from "@/foundation/attribution/tabs";
import { seriesColors } from "@/foundation/attribution/theme";
import { bucketForRange, funnelCounts, partnerDisplayName, partnerHeroFigures } from "@/foundation/attribution/viewModel";
import { DashboardFilterBar } from "@/foundation/attribution/DashboardFilterBar";
import { FeeDisclaimerBanner } from "@/foundation/attribution/Banners";
import { Hero } from "@/foundation/attribution/Hero";
import { Methodology } from "@/foundation/attribution/Methodology";
import { LoadFailure } from "@/foundation/attribution/LoadFailure";
import { UpdatedAt } from "@/foundation/attribution/UpdatedAt";
import {
  CountOverTimeSection,
  ExamBreakdownSection,
  FeeOverTimeSection,
  FunnelSection,
} from "@/foundation/attribution/Charts";
import {
  readFeeOverTime,
  readFunnel,
  readPartnerSummary,
  readSignupsOverTime,
  readVisitsOverTime,
} from "@/domains/partner/api";

const copy = getDashboardCopy("partner");

/**
 * A partner's dashboard: how the people they sent us are arriving, signing up
 * and what the estimated fee is.
 *
 * Four tabs. It never asks for, and never draws, revenue, margin or spend: the
 * partner endpoints do not return them and the view model has no field for them.
 * The partner is locked to the signed-in reporter's own, whatever the address says.
 */
export function PartnerDashboard({ partner }: { partner: string }) {
  const { filters, query, tab, setFilters, selectPreset, reset, setTab } = useAttributionState(
    "partner",
    partner,
  );
  const bucket = bucketForRange(query.from_date, query.to_date);

  const needsSummary = tab === "overview" || tab === "performance" || tab === "fee";
  const summary = useAsync(
    (signal) => (needsSummary ? readPartnerSummary(partner, query, signal) : Promise.resolve(null)),
    [partner, query, needsSummary],
  );
  const funnel = useAsync(
    (signal) => (tab === "overview" ? readFunnel(partner, query, signal) : Promise.resolve(null)),
    [partner, query, tab === "overview"],
  );
  const visits = useAsync(
    (signal) =>
      tab === "performance" ? readVisitsOverTime(partner, query, bucket, signal) : Promise.resolve(null),
    [partner, query, bucket, tab === "performance"],
  );
  const signups = useAsync(
    (signal) =>
      tab === "performance" ? readSignupsOverTime(partner, query, bucket, signal) : Promise.resolve(null),
    [partner, query, bucket, tab === "performance"],
  );
  const fee = useAsync(
    (signal) => (tab === "fee" ? readFeeOverTime(partner, query, bucket, signal) : Promise.resolve(null)),
    [partner, query, bucket, tab === "fee"],
  );

  // The moment the numbers on screen arrived.
  const updatedAt = useMemo(() => (summary.data ? new Date() : null), [summary.data]);

  const failure = (title: string, note?: string) =>
    function Failure(error: Error, retry: () => void) {
      return <LoadFailure title={title} error={error} onRetry={retry} note={note} />;
    };

  return (
    <div className="flex min-w-0 flex-col gap-5">
      <PageHeader
        title={`${partnerDisplayName(partner)} dashboard`}
        description="See how people from your links are using OSCE Guide. All dates are UK calendar days."
      />
      <B2CSegmentedTabs
        items={tabsForMode("partner").map((item) => ({ id: item.id, label: item.label }))}
        value={tab}
        onChange={setTab}
        aria-label="Partner dashboard sections"
      />
      <DashboardFilterBar
        filters={filters}
        onChange={setFilters}
        scope={filterScope(tab, "partner")}
        mode="partner"
        onPresetSelect={selectPreset}
        onReset={reset}
      />
      <UpdatedAt at={updatedAt} />

      {tab === "overview" ? (
        <div className="space-y-5">
          <AsyncBoundary
            state={summary}
            failure={failure("We couldn't load these numbers", "Nothing here is zero; it just hasn't loaded.")}
          >
            {(data) =>
              data ? (
                <>
                  <FeeDisclaimerBanner fee={data.fee} />
                  <Hero
                    copy={copy.hero}
                    mode="partner"
                    figures={partnerHeroFigures(data)}
                    counts={funnelCounts(funnel.data, {
                      visits: data.raw_arrival_count,
                      signups: data.acquired_user_count,
                      paid: data.paying_user_count,
                    })}
                  />
                </>
              ) : null
            }
          </AsyncBoundary>
          <AsyncBoundary state={funnel} failure={failure("We couldn't load the funnel", "")}>
            {(data) =>
              data ? (
                <FunnelSection copy={copy.funnel} counts={funnelCounts(data, { visits: 0, signups: 0, paid: 0 })} />
              ) : null
            }
          </AsyncBoundary>
        </div>
      ) : null}

      {tab === "performance" ? (
        <div className="space-y-5">
          <AsyncBoundary
            state={visits}
            failure={failure("We couldn't load performance", "Other sections are unaffected.")}
          >
            {(report) =>
              report ? (
                <CountOverTimeSection
                  title={copy.performance.visitsOverTime.title}
                  subtitle={copy.performance.visitsOverTime.subtitle}
                  emptyMessage={copy.performance.visitsOverTime.emptyMessage}
                  emptyHint={copy.performance.visitsOverTime.emptyHint}
                  report={report}
                  variant="bar"
                  color={seriesColors.linkVisits}
                  seriesName="Link visits"
                />
              ) : null
            }
          </AsyncBoundary>
          <AsyncBoundary state={signups} failure={() => null}>
            {(report) =>
              report ? (
                <CountOverTimeSection
                  title={copy.performance.signupsOverTime.title}
                  subtitle={copy.performance.signupsOverTime.subtitle}
                  emptyMessage={copy.performance.signupsOverTime.emptyMessage}
                  emptyHint={copy.performance.signupsOverTime.emptyHint}
                  report={report}
                  variant="area"
                  color={seriesColors.signups}
                  seriesName="Sign-ups"
                />
              ) : null
            }
          </AsyncBoundary>
          {filters.exam ? null : (
            <AsyncBoundary state={summary} failure={() => null}>
              {(data) =>
                data ? <ExamBreakdownSection copy={copy.performance.byExam} rows={data.breakdown_by_exam} /> : null
              }
            </AsyncBoundary>
          )}
        </div>
      ) : null}

      {tab === "fee" ? (
        <div className="space-y-5">
          <AsyncBoundary state={summary} failure={() => null}>
            {(data) => (data ? <FeeDisclaimerBanner fee={data.fee} /> : null)}
          </AsyncBoundary>
          <AsyncBoundary state={fee} failure={failure("We couldn't load the fee estimate", "")}>
            {(report) => (report ? <FeeOverTimeSection copy={copy.feeOverTime} report={report} /> : null)}
          </AsyncBoundary>
        </div>
      ) : null}

      {tab === "definitions" ? <Methodology copy={copy.methodology} mode="partner" /> : null}
    </div>
  );
}
