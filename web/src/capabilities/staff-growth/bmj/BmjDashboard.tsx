"use client";

import { useMemo } from "react";
import { AsyncBoundary, B2CSegmentedTabs, B2CPageHeader } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useAttributionState } from "@/capabilities/attribution-dashboard/useAttributionFilters";
import { getDashboardCopy } from "@/capabilities/attribution-dashboard/copy";
import { filterScope, tabsForMode } from "@/capabilities/attribution-dashboard/tabs";
import { bucketForRange, funnelCounts, internalHeroFigures } from "@/capabilities/attribution-dashboard/viewModel";
import { DashboardFilterBar } from "@/capabilities/attribution-dashboard/DashboardFilterBar";
import { SpendDisclaimerBanner } from "@/capabilities/attribution-dashboard/Banners";
import { Hero } from "@/capabilities/attribution-dashboard/Hero";
import { Methodology } from "@/capabilities/attribution-dashboard/Methodology";
import { LoadFailure } from "@/capabilities/attribution-dashboard/LoadFailure";
import { UpdatedAt } from "@/capabilities/attribution-dashboard/UpdatedAt";
import {
  CostVsRevenueSection,
  FunnelSection,
  RevenueByPlanSection,
  RevenueOverTimeSection,
} from "@/capabilities/attribution-dashboard/Charts";
import {
  readDashboardSummary,
  readPartnerFunnel,
  readRevenueOverTime,
} from "@/capabilities/staff-growth/api";
import { AnomaliesPanel } from "./AnomaliesPanel";
import { AcquiredUsersTable, ArrivalsTable } from "./ActivityTables";
import { PilotConfigPanel } from "./PilotConfigPanel";
import { ReconciliationPanel } from "./ReconciliationPanel";
import { ReportersPanel } from "./ReportersPanel";
import { TrackingReferences } from "./TrackingReferences";

const copy = getDashboardCopy("internal");

/**
 * The BMJ dashboard for staff: visits, sign-ups and money from a partner's links.
 *
 * Five tabs, one set of filters kept in the URL. Each number is read from the
 * server for exactly the dates, exam and campaign in the address, and a section
 * that fails says so and offers a retry instead of drawing zeros.
 */
export function BmjDashboard() {
  const { filters, query, tab, setFilters, selectPreset, reset, setTab } =
    useAttributionState("internal");
  const partner = filters.partner;
  const scope = filterScope(tab, "internal");

  const needsSummary = tab === "overview" || tab === "revenue" || tab === "definitions";
  const summary = useAsync(
    (signal) => (needsSummary ? readDashboardSummary(partner, query, signal) : Promise.resolve(null)),
    [partner, query, needsSummary],
  );
  const funnel = useAsync(
    (signal) => (tab === "overview" ? readPartnerFunnel(partner, query, signal) : Promise.resolve(null)),
    [partner, query, tab === "overview"],
  );
  const bucket = bucketForRange(query.from_date, query.to_date);
  const revenueOverTime = useAsync(
    (signal) =>
      tab === "revenue" ? readRevenueOverTime(partner, query, bucket, signal) : Promise.resolve(null),
    [partner, query, bucket, tab === "revenue"],
  );

  // The moment the numbers on screen arrived.
  const updatedAt = useMemo(() => (summary.data ? new Date() : null), [summary.data]);

  // `withoutNote` drops the reassurance that nothing shown is zero, where nothing is shown as zero.
  const summaryFailure = (title: string, withoutNote = false) =>
    function Failure(error: Error, retry: () => void) {
      return (
        <LoadFailure title={title} error={error} onRetry={retry} note={withoutNote ? "" : undefined} />
      );
    };

  return (
    <div className="flex min-w-0 flex-col gap-6">
      <B2CPageHeader
        title="BMJ dashboard"
        subtitle="Visits, sign-ups, and money from BMJ links."
      />
      <B2CSegmentedTabs
        items={tabsForMode("internal").map((item) => ({ id: item.id, label: item.label }))}
        value={tab}
        onChange={setTab}
        aria-label="Partner dashboard sections"
      />
      <DashboardFilterBar
        filters={filters}
        onChange={setFilters}
        scope={scope}
        mode="internal"
        onPresetSelect={selectPreset}
        onReset={reset}
      />
      <UpdatedAt at={updatedAt} />

      {tab === "overview" ? (
        <div className="space-y-5">
          <AsyncBoundary
            state={summary}
            failure={summaryFailure("We couldn't load these numbers")}
          >
            {(data) =>
              data ? (
                <>
                  <SpendDisclaimerBanner spend={data.spend} />
                  <AnomaliesPanel report={data.anomalies} />
                  <Hero
                    copy={copy.hero}
                    mode="internal"
                    figures={internalHeroFigures(data)}
                    counts={funnelCounts(funnel.data, {
                      visits: data.raw_arrival_count,
                      signups: data.acquired_user_count,
                      paid: data.revenue.paying_user_count,
                    })}
                  />
                </>
              ) : null
            }
          </AsyncBoundary>
          <AsyncBoundary state={funnel} failure={summaryFailure("We couldn't load the funnel", true)}>
            {(data) =>
              data ? (
                <FunnelSection
                  copy={copy.funnel}
                  counts={funnelCounts(data, { visits: 0, signups: 0, paid: 0 })}
                />
              ) : null
            }
          </AsyncBoundary>
        </div>
      ) : null}

      {tab === "revenue" ? (
        <div className="space-y-5">
          <AsyncBoundary state={summary} failure={summaryFailure("We couldn't load these numbers")}>
            {(data) =>
              data ? (
                <>
                  <SpendDisclaimerBanner spend={data.spend} />
                  <CostVsRevenueSection
                    subtitle={copy.internalCharts.costVsRevenueSubtitle}
                    spend={data.spend}
                  />
                </>
              ) : null
            }
          </AsyncBoundary>
          <AsyncBoundary
            state={revenueOverTime}
            failure={summaryFailure("We couldn't load revenue over time", true)}
          >
            {(report) =>
              report ? <RevenueOverTimeSection copy={copy.revenueOverTime} report={report} /> : null
            }
          </AsyncBoundary>
          <AsyncBoundary state={summary} failure={summaryFailure("We couldn't load revenue by plan", true)}>
            {(data) =>
              data ? (
                <RevenueByPlanSection copy={copy.revenueByPlan} rows={data.revenue.revenue_by_plan} />
              ) : null
            }
          </AsyncBoundary>
        </div>
      ) : null}

      {tab === "activity" ? (
        <div className="space-y-5">
          <ArrivalsTable partner={partner} query={query} description={copy.tables.arrivalsDescription} />
          <AcquiredUsersTable
            partner={partner}
            query={query}
            description={copy.tables.acquiredUsersDescription}
          />
        </div>
      ) : null}

      {tab === "definitions" ? (
        <div className="space-y-5">
          <Methodology copy={copy.methodology} mode="internal" />
          <AsyncBoundary state={summary} failure={summaryFailure("We couldn't load these numbers")}>
            {(data) =>
              data ? (
                <>
                  <ReconciliationPanel report={data.reconciliation} />
                  <AnomaliesPanel report={data.anomalies} />
                </>
              ) : null
            }
          </AsyncBoundary>
        </div>
      ) : null}

      {tab === "access" ? (
        <div className="space-y-5">
          <PilotConfigPanel partner={partner} />
          <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-2">
            <ReportersPanel partner={partner} />
            <TrackingReferences partner={partner} />
          </div>
        </div>
      ) : null}
    </div>
  );
}
