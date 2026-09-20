"use client";

import { PracticeOptions } from "@/capabilities/peer-practice/PracticeOptions";

import { useState } from "react";
import { AsyncBoundary, ButtonLink } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import {
  readDashboard,
  readPerformance,
  type Dashboard as DashboardData,
  type Performance,
} from "@/domains/train/api";
import {
  DashboardChartGrid,
  DashboardChartSide,
  DashboardChartWide,
  DashboardHeader,
} from "@/domains/train/dashboard/DashboardLayout";
import { AboutModal } from "@/domains/train/dashboard/AboutModals";
import { CompetencyHero } from "@/domains/train/dashboard/CompetencyHero";
import { DomainPerformanceCard } from "@/domains/train/dashboard/DomainPerformanceCard";
import { InsightsList } from "@/domains/train/dashboard/InsightsList";
import { PerformanceSummary } from "@/domains/train/dashboard/PerformanceSummary";
import { TrendCard } from "@/domains/train/dashboard/TrendCard";
import { WeeklyTrendCard } from "@/domains/train/dashboard/WeeklyTrendCard";
import { configFor } from "@/domains/train/dashboard/examConfig";
import { useDashboardExam } from "@/domains/train/dashboard/useDashboardExam";
import type { AboutKey } from "@/domains/train/dashboard/aboutTypes";

/**
 * Home for someone practising on their own — one screen for every exam.
 *
 * It replaces four: `sca/dashboard`, `plab/dashboard`, `casc/dashboard` and
 * `ortho/dashboard`, 8.4k lines whose differences were domain names, bar
 * colours, a maximum score, a threshold and the wording around them. Those are
 * rows in `examConfig` now. SCA is the one that is genuinely richer, and its
 * hero, weekly column and insights list are switched on by the same table.
 *
 * Two requests, not the old seven: `/me/dashboard` for who the person is and
 * what they hold, `/me/performance` for the marked work behind the charts.
 */
export function ExamDashboard() {
  const state = useAsync((signal) => readDashboard(signal), []);

  return (
    <AsyncBoundary state={state}>{(data) => <DashboardBody data={data} />}</AsyncBoundary>
  );
}

function DashboardBody({ data }: { data: DashboardData }) {
  const { session } = useSession();
  const { hrefFor } = useSurface();
  const { examCode, attempts } = useDashboardExam(data);
  const config = configFor(examCode);
  const [about, setAbout] = useState<AboutKey | null>(null);

  /*
   * Wrapped in an object so a 404 — the endpoint is not built yet — is a
   * successful load of nothing rather than a null the boundary would read as
   * "render nothing". A real failure still reaches the boundary and is shown
   * with a retry, which is the rule that "no data" must never mean "it broke".
   */
  const performanceState = useAsync(
    async (signal) => ({ performance: await readPerformance(examCode, signal) }),
    [examCode],
  );

  const firstName = session?.user.name?.split(" ")[0] ?? "there";
  const subtitle = config.subtitle ? `Welcome back, ${firstName}. ${config.subtitle}` : undefined;
  const eyebrow = config.sections.hero
    ? `${attempts} station${attempts === 1 ? "" : "s"} attempted`
    : undefined;

  return (
    <>
      <DashboardHeader
        title={config.title}
        eyebrow={eyebrow}
        subtitle={subtitle}
        actions={
          <>
            <ButtonLink href={hrefFor("/mocks")} variant="primary" size="md">
              {attempts === 0 ? "Start your first station" : "Practise a station"}
            </ButtonLink>
          </>
        }
      />

      <AsyncBoundary state={performanceState}>
        {({ performance }) => (
          <ExamSections
            config={config}
            performance={performance}
            loading={performanceState.loading}
            onAbout={setAbout}
          />
        )}
      </AsyncBoundary>

          <PracticeOptions />
      <AboutModal config={config} active={about} onClose={() => setAbout(null)} />
    </>
  );
}

function ExamSections({
  config,
  performance,
  loading,
  onAbout,
}: {
  config: ReturnType<typeof configFor>;
  performance: Performance | null;
  loading: boolean;
  onAbout: (key: AboutKey) => void;
}) {
  const summary = performance?.summary ?? null;

  return (
    <div className="mb-6 space-y-5 sm:mb-8">
      {config.sections.hero ? (
        <div className="flex flex-col gap-5 xl:flex-row xl:items-stretch">
          <div className="min-w-0 flex-1">
            <CompetencyHero className="h-full" summary={summary} loading={loading} />
          </div>
          {config.sections.weeklyTrend ? (
            <WeeklyTrendCard
              className="h-full"
              trend={performance?.trend ?? null}
              loading={loading}
            />
          ) : null}
        </div>
      ) : (
        <PerformanceSummary
          config={config}
          summary={summary}
          loading={loading}
          onAbout={() => onAbout("summary")}
        />
      )}

      <DashboardChartGrid>
        <DashboardChartWide>
          <DomainPerformanceCard
            config={config}
            domains={performance?.domains ?? null}
            loading={loading}
            onAbout={() => onAbout("domain")}
          />
        </DashboardChartWide>
        <DashboardChartSide>
          <TrendCard
            config={config}
            trend={performance?.trend ?? null}
            loading={loading}
            onAbout={() => onAbout("trend")}
          />
        </DashboardChartSide>
      </DashboardChartGrid>

      {config.sections.insights ? (
        <InsightsList items={[]} loading={loading} onAbout={() => onAbout("summary")} />
      ) : null}
    </div>
  );
}
