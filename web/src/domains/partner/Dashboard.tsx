"use client";

import { useMemo } from "react";
import { AsyncBoundary, B2CSegmentedTabs, b2bTokens, cn } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { formatChartPeriodLabel } from "@/capabilities/attribution-dashboard/presets";
import { useAttributionState } from "@/capabilities/attribution-dashboard/useAttributionFilters";
import { getDashboardCopy } from "@/capabilities/attribution-dashboard/copy";
import { tabsForMode } from "@/capabilities/attribution-dashboard/tabs";
import {
  asBucket,
  bucketForRange,
  countPoints,
  examShareRows,
  feePoints,
  funnelCounts,
  funnelStepViews,
  heroHasData,
  heroStats,
  partnerHeroFigures,
  visibleDefinitions,
} from "@/capabilities/attribution-dashboard/viewModel";
import { LoadFailure } from "@/capabilities/attribution-dashboard/LoadFailure";
import { formatMoney } from "@/foundation/format";
import {
  readFeeOverTime,
  readPartnerSummary,
  readSignupsOverTime,
  readVisitsOverTime,
} from "@/domains/partner/api";
import { readPartnerFunnel } from "@/capabilities/staff-growth/api";
import {
  Bars,
  Definition,
  FilterCard,
  FeeNote,
  PartnerCard,
  PartnerHeader,
  Row,
  RowList,
  Tile,
  Tiles,
} from "@/domains/partner/PartnerParts";

const copy = getDashboardCopy("partner");

/** "northern-deanery" reads "Northern Deanery"; the workspace's own name wins when it has one. */
function titleCase(slug: string): string {
  return slug.replace(/[-_]+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/** "1,240" and "£496": thousands separated, whole pounds without pence. */
function readable(value: string): string {
  return /^\d+$/.test(value) ? Number(value).toLocaleString("en-GB") : value.replace(/\.00$/, "");
}

function Empty({ title, hint }: { title: string; hint: string }) {
  return (
    <div>
      <b className="font-semibold">{title}</b>
      <div className={b2bTokens.assessMeta}>{hint}</div>
    </div>
  );
}

/**
 * A partner's dashboard: how the people they sent us are arriving, signing up
 * and what the estimated fee is.
 *
 * Four tabs. It never asks for, and never draws, revenue, margin or spend: the
 * partner endpoints do not return them and the view model has no field for them.
 * The partner is locked to the signed-in reporter's own, whatever the address says.
 */
export function PartnerDashboard({ partner, name }: { partner: string; name?: string }) {
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
    (signal) => (tab === "overview" ? readPartnerFunnel(partner, query, signal) : Promise.resolve(null)),
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

  const fail = (title: string, note = "Other sections are unaffected.") =>
    function Failure(error: Error, retry: () => void) {
      return <LoadFailure title={title} error={error} onRetry={retry} note={note} />;
    };

  const series = (report: Parameters<typeof countPoints>[0]) =>
    countPoints(report).map((point) => ({
      label: formatChartPeriodLabel(point.period, asBucket(report.bucket)),
      value: point.value,
      text: String(point.value),
    }));

  return (
    <section aria-label="Partner dashboard" className={cn(b2bTokens.assessPage, "!w-auto")}>
      <PartnerHeader
        title={`${name ?? titleCase(partner)} dashboard`}
        lead="See how people from your links are using OSCE Guide. All dates are UK calendar days."
      />
      <div data-board-hide>
        <B2CSegmentedTabs
          items={tabsForMode("partner").map((item) => ({ id: item.id, label: item.label }))}
          value={tab}
          onChange={setTab}
          className="!mb-0"
          aria-label="Partner dashboard sections"
        />
      </div>
      {tab !== "definitions" ? (
        <FilterCard filters={filters} onChange={setFilters} onPresetSelect={selectPreset} onReset={reset} updatedAt={updatedAt} />
      ) : null}

      {tab === "overview" ? (
        <>
          <FeeNote fee={summary.data?.fee} />
          <AsyncBoundary state={summary} failure={fail("We couldn't load these numbers", "Nothing here is zero; it just hasn't loaded.")}>
            {(data) => {
              if (!data) return null;
              const figures = partnerHeroFigures(data);
              return (
                <PartnerCard eyebrow={copy.hero.sectionLabel} title={copy.hero.title} lead={copy.hero.hint}>
                  {heroHasData(figures) ? (
                    <Tiles>
                      {heroStats("partner", figures, copy.hero).map((stat) => (
                        <Tile key={stat.key} label={stat.label} value={readable(stat.value)} note={stat.tooltip} />
                      ))}
                    </Tiles>
                  ) : (
                    <Empty title={copy.hero.emptyTitle} hint={copy.hero.emptyDetail} />
                  )}
                </PartnerCard>
              );
            }}
          </AsyncBoundary>
          <AsyncBoundary state={funnel} failure={fail("We couldn't load the funnel", "")}>
            {(data) => {
              if (!data) return null;
              // The funnel route counts only what it knows; the summary's numbers stand in when it has none.
              const known = data.steps?.some((step) => (step.count ?? 0) > 0);
              const figures = summary.data;
              const steps = funnelStepViews(
                funnelCounts(known ? data : null, {
                  visits: figures?.raw_arrival_count ?? 0,
                  signups: figures?.acquired_user_count ?? 0,
                  paid: figures?.paying_user_count ?? 0,
                }),
              );
              return (
                <PartnerCard title="From visit to payment" lead="How many people reached each step">
                  {steps.some((step) => (step.count ?? 0) > 0) ? (
                    <Tiles>
                      {steps.map((step) => (
                        <Tile
                          key={step.key}
                          label={step.label}
                          value={readable(String(step.count ?? "-"))}
                          note={`${step.key === "landing" ? 100 : (step.percentOfVisits ?? 0)}% of visits`}
                        />
                      ))}
                    </Tiles>
                  ) : (
                    <Empty title={copy.funnel.emptyMessage} hint={copy.funnel.emptyHint} />
                  )}
                </PartnerCard>
              );
            }}
          </AsyncBoundary>
        </>
      ) : null}

      {tab === "performance" ? (
        <>
          <AsyncBoundary state={visits} failure={fail("We couldn't load performance")}>
            {(report) =>
              report ? (
                <PartnerCard title={copy.performance.visitsOverTime.title} lead={copy.performance.visitsOverTime.subtitle}>
                  {series(report).some((point) => point.value > 0) ? (
                    <Bars points={series(report)} summary={copy.performance.visitsOverTime.title} />
                  ) : (
                    <Empty title={copy.performance.visitsOverTime.emptyMessage} hint={copy.performance.visitsOverTime.emptyHint} />
                  )}
                </PartnerCard>
              ) : null
            }
          </AsyncBoundary>
          <AsyncBoundary state={signups} failure={fail("We couldn't load sign-ups over time")}>
            {(report) =>
              report ? (
                <PartnerCard title={copy.performance.signupsOverTime.title} lead={copy.performance.signupsOverTime.subtitle}>
                  {series(report).some((point) => point.value > 0) ? (
                    <Bars points={series(report)} summary={copy.performance.signupsOverTime.title} />
                  ) : (
                    <Empty title={copy.performance.signupsOverTime.emptyMessage} hint={copy.performance.signupsOverTime.emptyHint} />
                  )}
                </PartnerCard>
              ) : null
            }
          </AsyncBoundary>
          {filters.exam ? null : (
            <AsyncBoundary state={summary} failure={fail("We couldn't load the breakdown by exam")}>
              {(data) => {
                if (!data) return null;
                const rows = examShareRows(data.breakdown_by_exam);
                return (
                  <PartnerCard title={copy.performance.byExam.title} lead={copy.performance.byExam.description}>
                    {rows.some((row) => row.visits > 0) ? (
                      rows.map((row) => (
                        <Row key={row.exam}>
                          {row.exam} <span className={b2bTokens.assessMeta}>{row.sharePercent}% of visits</span>
                          <span className={cn(b2bTokens.assessMeta, "ml-auto")}>{row.visits} visits, {row.signups} sign-ups</span>
                        </Row>
                      ))
                    ) : (
                      <Empty title="Nothing to show for these dates" hint="Try widening the date range or removing filters." />
                    )}
                  </PartnerCard>
                );
              }}
            </AsyncBoundary>
          )}
        </>
      ) : null}

      {tab === "fee" ? (
        <>
          <FeeNote fee={summary.data?.fee} />
          <AsyncBoundary state={fee} failure={fail("We couldn't load the fee estimate", "")}>
            {(report) => {
              if (!report) return null;
              const bucket = asBucket(report.bucket);
              const points = feePoints(report).map((point) => ({
                label: formatChartPeriodLabel(point.period, bucket),
                value: point.value,
                text: `${formatMoney(point.value)} (${point.extra ?? 0} visits)`,
              }));
              return (
                <PartnerCard title={copy.feeOverTime.title} lead={copy.feeOverTime.subtitleByBucket[bucket] ?? copy.feeOverTime.defaultSubtitle}>
                  {points.some((point) => point.value > 0) ? (
                    <Bars points={points} summary={copy.feeOverTime.title} />
                  ) : (
                    <Empty title={copy.feeOverTime.emptyMessage} hint={copy.feeOverTime.emptyHint} />
                  )}
                </PartnerCard>
              );
            }}
          </AsyncBoundary>
        </>
      ) : null}

      {tab === "definitions" ? (
        <PartnerCard title={copy.methodology.introTitle} lead={copy.methodology.introBody}>
          <div className={b2bTokens.assessEyebrow}>{copy.methodology.definitionsHeading}</div>
          <RowList>
            {visibleDefinitions("partner", copy.methodology.definitions).map((item, index) => (
              <Definition key={item.term} term={item.term} detail={item.detail} first={index === 0} />
            ))}
          </RowList>
          <div className={b2bTokens.assessEyebrow}>{copy.methodology.rulesHeading}</div>
          <RowList>
            {copy.methodology.rules.map((item, index) => (
              <Definition key={item.term} term={item.term} detail={item.detail} first={index === 0} />
            ))}
          </RowList>
        </PartnerCard>
      ) : null}
    </section>
  );
}
