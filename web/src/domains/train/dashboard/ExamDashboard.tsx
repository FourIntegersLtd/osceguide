"use client";

import { PracticeOptions } from "@/capabilities/peer-practice/PracticeOptions";

import { useEffect, useState } from "react";
import { AsyncBoundary, ButtonLink, Modal } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { ExamWishes } from "@/capabilities/account";
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
import { ExamDateControl } from "@/domains/train/dashboard/ExamDateControl";
import { examCountdownSubtitle, isExamWeek } from "@/domains/train/dashboard/examDate";
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
  const [showExamWishes, setShowExamWishes] = useState(false);

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

  const examDate = session?.user.exam_date ?? null;
  const userId = session?.user.id ?? null;

  /*
   * The retiring dashboard showed its "Good luck this week" note once, in the
   * seven days before the exam, and remembered that it had via localStorage so
   * it did not re-open on every visit. Same trigger, same one-time guard.
   */
  useEffect(() => {
    if (!examDate || !userId) return;
    if (!isExamWeek(examDate)) return;
    const key = `examWishesShown-${userId}`;
    if (window.localStorage.getItem(key)) return;
    window.localStorage.setItem(key, "true");
    // A one-time modal fired off reading/writing localStorage — the effect is
    // synchronising with that external store, which is what it is for.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setShowExamWishes(true);
  }, [examDate, userId]);

  const firstName = session?.user.name?.split(" ")[0] ?? "there";
  // The countdown leads when there is one to show; otherwise the exam's own
  // welcome line (SCA has none, matching the old screen).
  const subtitle =
    examCountdownSubtitle(examDate) ??
    (config.subtitle ? `Welcome back, ${firstName}. ${config.subtitle}` : undefined);
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
            <ExamDateControl />
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

      {showExamWishes && (
        <Modal width="min(95vw, 480px)" height="fit-content" onClose={() => setShowExamWishes(false)}>
          <ExamWishes />
        </Modal>
      )}
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
