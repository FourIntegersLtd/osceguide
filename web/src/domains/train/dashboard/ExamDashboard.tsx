"use client";


import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { HiOutlineChartBar, HiOutlineMicrophone } from "react-icons/hi2";
import {
  AsyncBoundary,
  B2CGroupedRowLink,
  B2CGroupedSection,
  B2CPageHeader,
  ButtonLink,
  Modal,
  TextLink,
  productTokens,
} from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { ExamWishes } from "@/capabilities/account";
import { attemptKindLabel } from "@/capabilities/transcripts/kindLabel";
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
import type { components } from "@/foundation/platform-client/schema";
import { AboutModal } from "@/domains/train/dashboard/AboutModals";
import { CompetencyHero } from "@/domains/train/dashboard/CompetencyHero";
import { DomainPerformanceCard } from "@/domains/train/dashboard/DomainPerformanceCard";
import { InsightsList } from "@/domains/train/dashboard/InsightsList";
import RagCompositionBars from "@/foundation/charts/RagCompositionBars";
import CategoryVolumeList from "@/foundation/charts/CategoryVolumeList";
import { PerformanceSummary } from "@/domains/train/dashboard/PerformanceSummary";
import { TrendCard } from "@/domains/train/dashboard/TrendCard";
import { WeeklyTrendCard } from "@/domains/train/dashboard/WeeklyTrendCard";
import { dashboardView, nextStationCopy, recentAttemptStatus, type DashboardView } from "@/domains/train/dashboard/dashboardView";
import { useDashboardExam } from "@/domains/train/dashboard/useDashboardExam";
import { BadgeStrip } from "@/domains/train/dashboard/BadgeStrip";
import { ExamDateControl } from "@/domains/train/dashboard/ExamDateControl";
import { daysBetween } from "@/foundation/ui/dateDay";
import { isExamWeek } from "@/domains/train/dashboard/examDate";
import type { AboutKey } from "@/domains/train/dashboard/aboutTypes";
import { B2CHero } from "@/foundation/ui/B2CHero";

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

  const performanceState = useAsync((signal) => readPerformance(examCode, signal), [examCode]);

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
  const greeting = attempts === 0 ? `Welcome, ${firstName}.` : `Welcome back, ${firstName}.`;
  const eyebrow = `${attempts} station${attempts === 1 ? "" : "s"} attempted`;
  const performance = performanceState.data;
  const view = dashboardView(performance);

  return (
    <>
      <p className="mb-2 text-osce-body text-b2c-text-muted">{greeting}</p>
      <B2CPageHeader eyebrow={eyebrow} title={view.title} action={<ExamDateControl />} />

      <NextStation
        practiseHref={hrefFor("/mocks")}
        firstStation={attempts === 0}
        weakest={view.counted ? (view.insights[0]?.text ?? null) : null}
      />

      <BadgeStrip />

      {attempts === 0 ? (
        <>
          <div className="flex flex-col items-center gap-2.5 rounded-osce-lg border border-dashed border-b2c-border bg-osce-surface px-6 py-10 text-center">
            <span className="flex h-10 w-10 items-center justify-center rounded-osce-md bg-b2c-surface-muted text-osce-ink-700">
              <HiOutlineChartBar className="h-5 w-5" aria-hidden />
            </span>
            <h2 className={productTokens.b2cSectionTitle}>No assessments yet</h2>
            <p className="max-w-[360px] text-b2c-text-muted">
              Complete a session to see your strengths and weak spots here.
            </p>
          </div>
          <RecentStations
            recent={data.recent_attempts ?? []}
            attemptHref={(id) => hrefFor(`/attempts/${id}`)}
            sessionsHref={hrefFor("/transcripts")}
          />
        </>
      ) : (
      <AsyncBoundary state={performanceState}>
        {() => (
          <ExamSections
            view={view}
            performance={performance}
            loading={performanceState.loading}
            onAbout={setAbout}
            recent={data.recent_attempts ?? []}
            attemptHref={(id) => hrefFor(`/attempts/${id}`)}
            sessionsHref={hrefFor("/transcripts")}
          />
        )}
      </AsyncBoundary>
      )}

      <AboutModal view={view} active={about} onClose={() => setAbout(null)} />

      {showExamWishes && !showOnboarding && (
        <Modal width="min(95vw, 480px)" height="fit-content" onClose={() => setShowExamWishes(false)}>
          <ExamWishes />
        </Modal>
      )}

      {showOnboarding && (
        <Modal width="min(95vw, 560px)" height="fit-content" onClose={dismissOnboarding} hideCloseButton>
          <OnboardingFlow onComplete={completeOnboarding} onSkip={dismissOnboarding} />
        </Modal>
      )}
    </>
  );
}

type RecentAttempt = components["schemas"]["RecentAttempt"];

/**
 * The one hero (canvas `train-dashboard`): what to do next and why. Where the
 * rubric counts grades it names the weakest domain; otherwise it just says
 * "practise".
 */
function NextStation({
  practiseHref,
  firstStation,
  weakest,
}: {
  practiseHref: string;
  firstStation: boolean;
  weakest: string | null;
}) {
  const { title, sub } = nextStationCopy({ firstStation, weakest });
  return (
    <B2CHero
      lead
      eyebrow={firstStation ? undefined : "Your next station"}
      title={title}
      action={
        <>
          <ButtonLink href={practiseHref} variant="primary" size="md">
            {firstStation ? "Start your first session" : "Practise a station"}
          </ButtonLink>
          {weakest ? (
            <ButtonLink href="#work" variant="secondary" size="md">
              See what to work on
            </ButtonLink>
          ) : null}
        </>
      }
    >
      {sub}
    </B2CHero>
  );
}

function RecentStations({
  recent,
  attemptHref,
  sessionsHref,
}: {
  recent: RecentAttempt[];
  attemptHref: (id: string) => string;
  sessionsHref: string;
}) {
  if (recent.length === 0) return null;
  return (
    <B2CGroupedSection eyebrow="Recent stations" action={<TextLink href={sessionsHref}>All sessions</TextLink>}>
      {recent.slice(0, 5).map((attempt) => (
        <B2CGroupedRowLink
          key={attempt.id}
          href={attemptHref(attempt.id)}
          icon={HiOutlineMicrophone}
          title={attemptKindLabel(attempt.kind)}
          meta={`${relativeDay(attempt.created_at)} · ${attempt.exam_code.toUpperCase()}`}
          trailing={
            <span className="hidden h-[22px] shrink-0 items-center rounded-osce-sm bg-b2c-surface-muted px-2 text-osce-caption font-medium text-osce-ink-700 sm:inline-flex">
              {recentAttemptStatus(attempt)}
            </span>
          }
        />
      ))}
    </B2CGroupedSection>
  );
}

function relativeDay(value: string): string {
  const at = new Date(value);
  if (Number.isNaN(at.getTime())) return value;
  const days = daysBetween(at, new Date());
  if (days <= 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return at.toLocaleDateString("en-GB", { weekday: "long" });
  return at.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

function ExamSections({
  view,
  performance,
  loading,
  onAbout,
  recent,
  attemptHref,
  sessionsHref,
}: {
  view: DashboardView;
  performance: Performance | null;
  loading: boolean;
  onAbout: (key: AboutKey) => void;
  recent: RecentAttempt[];
  attemptHref: (id: string) => string;
  sessionsHref: string;
}) {
  const grid = "grid grid-cols-1 items-stretch gap-6 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]";
  return (
    <div className="space-y-6">
      {view.versionNotice ? (
        <p className="rounded-control bg-b2c-surface-muted px-4 py-2.5 text-osce-meta text-b2c-text-muted">
          {view.versionNotice}. Totals are compared as each version defines them.
        </p>
      ) : null}

      {view.counted ? (
        <div className={grid}>
          <CompetencyHero mix={performance ? view.hero : null} loading={loading} onAbout={() => onAbout("summary")} />
          <WeeklyTrendCard trend={performance?.trend ?? null} loading={loading} />
        </div>
      ) : view.summaryCards.length > 0 ? (
        <PerformanceSummary cards={view.summaryCards} loading={loading} onAbout={() => onAbout("summary")} />
      ) : null}

      <div className={grid}>
        <DomainPerformanceCard chart={view.domainChart} loading={loading} onAbout={() => onAbout("domain")} />
        {view.counted ? (
          <div id="work" className="scroll-mt-24">
            <InsightsList items={view.insights} loading={loading} />
          </div>
        ) : (
          <TrendCard scale={view.trend} loading={loading} onAbout={() => onAbout("trend")} />
        )}
      </div>

      {view.bands.length > 0 ? (
        <div className="flex flex-wrap items-center gap-2 text-osce-meta text-b2c-text-muted">
          <span className="font-medium text-osce-ink-700">Station bands</span>
          {view.bands.map((band) => (
            <span key={band} className="inline-flex h-[22px] items-center rounded-osce-sm bg-b2c-surface-muted px-2 text-osce-caption font-medium text-osce-ink-700">
              {band}
            </span>
          ))}
        </div>
      ) : null}

      {view.composition.length > 0 && !view.counted ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <RagCompositionBars data={view.composition} emptyHint="Complete a station to see how each domain went." />
          <CategoryVolumeList data={view.composition} />
        </div>
      ) : null}

      <RecentStations recent={recent} attemptHref={attemptHref} sessionsHref={sessionsHref} />
    </div>
  );
}
