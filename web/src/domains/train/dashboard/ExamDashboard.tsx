"use client";


import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AsyncBoundary, ButtonLink, Modal } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { ExamWishes } from "@/capabilities/account";
import {
  OnboardingFlow,
  needsDashboardOnboarding,
  rememberOnboardingSeen,
} from "@/capabilities/onboarding";
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
import RagCompositionBars from "@/foundation/charts/RagCompositionBars";
import CategoryVolumeList from "@/foundation/charts/CategoryVolumeList";
import { PerformanceSummary } from "@/domains/train/dashboard/PerformanceSummary";
import { TrendCard } from "@/domains/train/dashboard/TrendCard";
import { WeeklyTrendCard } from "@/domains/train/dashboard/WeeklyTrendCard";
import { dashboardView, type DashboardView } from "@/domains/train/dashboard/dashboardView";
import { useDashboardExam } from "@/domains/train/dashboard/useDashboardExam";
import { ExamDateControl } from "@/domains/train/dashboard/ExamDateControl";
import { examCountdownSubtitle, examMoment, isExamWeek } from "@/domains/train/dashboard/examDate";
import type { AboutKey } from "@/domains/train/dashboard/aboutTypes";

/**
 * Home for someone practising on their own — one screen for every exam.
 *
 * It replaces four: `sca/dashboard`, `plab/dashboard`, `casc/dashboard` and
 * `ortho/dashboard`, 8.4k lines whose differences were domain names, a maximum
 * score, a threshold and the wording around them. All of that is the rubric's
 * display now, sent with `/me/performance` and read by `dashboardView`; no
 * line here names an exam. A rubric that counts grades (SCA) gets the
 * competency hero, weekly column and "what to work on" list because of how it
 * sums, not because of its code.
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
  const router = useRouter();
  const { examCode, attempts } = useDashboardExam(data);
  const [about, setAbout] = useState<AboutKey | null>(null);
  const [showExamWishes, setShowExamWishes] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);

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

  const examDate = examMoment(session?.user.exam_date, session?.user.exam_time);
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

  /*
   * The retiring dashboard opened onboarding as a modal, unprompted, for a
   * brand-new user: no marked work yet, and never finished or closed it
   * (remembered in localStorage per exam and per user). Same trigger here;
   * localStorage is an external store, so it is read in an effect rather than
   * during render.
   */
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setShowOnboarding(needsDashboardOnboarding(examCode, userId, attempts));
  }, [examCode, userId, attempts]);

  const dismissOnboarding = () => {
    if (userId) rememberOnboardingSeen(examCode, userId);
    setShowOnboarding(false);
  };

  // Finishing sends the person to the mocks list, where a first consultation
  // starts — the same hand-off the retiring dashboard made.
  const completeOnboarding = () => {
    dismissOnboarding();
    router.push(hrefFor("/mocks"));
  };

  const firstName = session?.user.name?.split(" ")[0] ?? "there";
  // The countdown leads when there is one to show; otherwise the exam's own
  // welcome line (SCA has none, matching the old screen).
  const subtitle = examCountdownSubtitle(examDate) ?? `Welcome back, ${firstName}.`;
  const eyebrow = `${attempts} station${attempts === 1 ? "" : "s"} attempted`;
  const performance = performanceState.data?.performance ?? null;
  const view = dashboardView(performance);

  return (
    <>
      <DashboardHeader
        title={view.title}
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
        {() => (
          <ExamSections
            view={view}
            performance={performance}
            loading={performanceState.loading}
            onAbout={setAbout}
          />
        )}
      </AsyncBoundary>

      <AboutModal view={view} active={about} onClose={() => setAbout(null)} />

      {showExamWishes && !showOnboarding && (
        <Modal width="min(95vw, 480px)" height="fit-content" onClose={() => setShowExamWishes(false)}>
          <ExamWishes />
        </Modal>
      )}

      {showOnboarding && (
        <Modal width="min(95vw, 560px)" height="fit-content" onClose={dismissOnboarding}>
          <OnboardingFlow onComplete={completeOnboarding} />
        </Modal>
      )}
    </>
  );
}

function ExamSections({
  view,
  performance,
  loading,
  onAbout,
}: {
  view: DashboardView;
  performance: Performance | null;
  loading: boolean;
  onAbout: (key: AboutKey) => void;
}) {
  return (
    <div className="mb-6 space-y-5 sm:mb-8">
      {view.versionNotice ? (
        <p className="rounded-lg border border-b2c-border-light bg-b2c-surface-muted px-4 py-2 text-osce-meta text-b2c-text-secondary">
          {view.versionNotice}. Totals are compared as each version defines them.
        </p>
      ) : null}

      {view.counted ? (
        <div className="flex flex-col gap-5 xl:flex-row xl:items-stretch">
          <div className="min-w-0 flex-1">
            <CompetencyHero className="h-full" mix={performance ? view.hero : null} loading={loading} />
          </div>
          <WeeklyTrendCard className="h-full" trend={performance?.trend ?? null} loading={loading} />
        </div>
      ) : view.summaryCards.length > 0 ? (
        <PerformanceSummary cards={view.summaryCards} loading={loading} onAbout={() => onAbout("summary")} />
      ) : null}

      <DashboardChartGrid>
        <DashboardChartWide>
          <DomainPerformanceCard chart={view.domainChart} loading={loading} onAbout={() => onAbout("domain")} />
        </DashboardChartWide>
        <DashboardChartSide>
          <TrendCard scale={view.trend} loading={loading} onAbout={() => onAbout("trend")} />
        </DashboardChartSide>
      </DashboardChartGrid>

      {view.bands.length > 0 ? (
        <div className="flex flex-wrap items-center gap-2 text-osce-meta text-b2c-text-secondary">
          <span className="font-medium text-osce-ink-700">Station bands</span>
          {view.bands.map((band) => (
            <span key={band} className="rounded-full border border-b2c-border-light bg-b2c-surface-muted px-2.5 py-0.5">
              {band}
            </span>
          ))}
        </div>
      ) : null}

      {view.composition.length > 0 ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <RagCompositionBars data={view.composition} emptyHint="Complete a station to see how each domain went." />
          <CategoryVolumeList data={view.composition} />
        </div>
      ) : null}

      {view.counted ? (
        <InsightsList items={view.insights} loading={loading} onAbout={() => onAbout("summary")} />
      ) : null}
    </div>
  );
}

