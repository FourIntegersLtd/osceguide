"use client";

import { boardBtn, boardChip } from "@/foundation/ui/boardKit";
import Link from "next/link";
import { useState, type ReactNode } from "react";
import {
  Alert,
  AsyncBoundary,
  Button,
  Spinner,
  b2bTokens,
  cn,
} from "@/foundation/ui";
import { humanise } from "@/foundation/format";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { readOrgDashboard, readSupervisorCircuits, type OrgDashboard as Data } from "@/domains/assess/dashboard/api";
import { BoardRow, BoardSection, RowChevron, RowText } from "@/domains/assess/dashboard/BoardParts";
import { HireAttention, HireHeader } from "@/domains/assess/dashboard/HireParts";
import { LiveNow } from "@/domains/assess/dashboard/LiveNow";
import { SetupAssistant } from "@/domains/assess/dashboard/SetupAssistant";
import { NextCircuit, SupervisorCircuits } from "@/domains/assess/dashboard/SupervisorCircuits";
import {
  attentionFromResults,
  comingUp,
  dateEyebrow,
  dateTile,
  modeLabel,
  notJoinedItem,
  sittingTally,
  todayGreeting,
  todaySentence,
  type AttentionItem,
} from "@/domains/assess/dashboard/support";
import { assistantSteps, NEW_EXAM_PATH, SCHEDULE_SITTING_PATH, setupComplete, setupTiles } from "@/domains/assess/dashboard/setupSteps";
import { readResultsIndex } from "@/domains/assess/results/api";
import { StationsToReview, useStationsToReview } from "@/domains/assess/results/StationsToReview";
import { useAssessWords } from "@/domains/assess/useAssessWords";

/**
 * The institution's home screen.
 *
 * Until a first sitting is possible an administrator sees the setup assistant; afterwards
 * "Today". A supervisor's circuits show for whoever may run them, so a supervisor who is also
 * an admin sees both halves rather than whichever a role check picked.
 */
export function OrgDashboard({ orgSlug }: { orgSlug: string }) {
  const state = useAsync((signal) => readOrgDashboard(orgSlug, signal), [orgSlug]);
  const { session } = useSession();
  const admin = can(session, "manage_team");
  const runs = can(session, "run_circuits");

  return (
    <div className="flex w-full min-w-0 flex-col gap-6">
      <AsyncBoundary state={state}>
        {(data) => <Body data={data} orgSlug={orgSlug} admin={admin} runs={runs} />}
      </AsyncBoundary>
    </div>
  );
}

function Body({ data, orgSlug, admin, runs }: { data: Data; orgSlug: string; admin: boolean; runs: boolean }) {
  const w = useAssessWords();
  const { session } = useSession();
  const settingUp = admin && !setupComplete(assistantSteps(data.setup, w));

  if (settingUp) {
    return (
      <div className={b2bTokens.assessPage}>
        <SetupAssistant orgName={data.name} setup={data.setup} />
        <Counts data={data} setup />
      </div>
    );
  }
  return <Today data={data} orgSlug={orgSlug} admin={admin} runs={runs} name={session?.user.name} />;
}

/** A supervisor's header: how many of their stations still need a review. */
function SupervisorHeader({ orgSlug, eyebrow }: { orgSlug: string; eyebrow: string }) {
  const { stations } = useStationsToReview(orgSlug);
  const count = stations.length;
  return (
    <PageHead
      eyebrow={eyebrow}
      title={`${count === 0 ? "No" : count} ${count === 1 ? "station" : "stations"} to review`}
      description="You review the circuits you lead. Your ratings are what count; the AI mark is a starting point."
    />
  );
}

/** The board's page head: eyebrow, h1, one line and, when there is one, the screen's action. */
function PageHead({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <div className={b2bTokens.assessEyebrow}>{eyebrow}</div>
        <h1 className={b2bTokens.assessTitle}>{title}</h1>
        <p className={b2bTokens.assessDesc}>{description}</p>
      </div>
      {action}
    </div>
  );
}

function Today({ data, orgSlug, admin, runs, name }: { data: Data; orgSlug: string; admin: boolean; runs: boolean; name?: string }) {
  const w = useAssessWords();
  const { hrefFor } = useSurface();
  const { session } = useSession();
  const schedules = can(session, "schedule_sittings");
  const upcoming = comingUp(data.recent_sittings ?? []);
  const [running, setRunning] = useState(0);
  const [statusHost, setStatusHost] = useState<HTMLElement | null>(null);
  const mayDecide = can(session, "sign_off_results");
  const results = useAsync((signal) => (mayDecide ? readResultsIndex(orgSlug, signal) : Promise.resolve(null)), [orgSlug, mayDecide]);
  const notJoined = can(session, "manage_team") ? notJoinedItem(data.counts.invited_not_joined, w) : null;
  const attention = [...attentionFromResults(results.data?.rows ?? [], w), ...(notJoined ? [notJoined] : [])];
  const circuits = useAsync((signal) => (runs ? readSupervisorCircuits(orgSlug, signal) : Promise.resolve(null)), [orgSlug, runs]);
  const circuitRows = circuits.data?.items ?? [];
  const earlier = (data.recent_sittings ?? []).filter((sitting) => sitting.status !== "scheduled");

  const scheduleAction = data.setup.ready_to_run ? (
    <Link href={hrefFor(SCHEDULE_SITTING_PATH)} className={boardBtn("primary")}>
      {w.scheduleSitting}
    </Link>
  ) : (
    <div className="flex flex-col items-end gap-1">
      <Button themeType="b2b" variant="commit" disabled aria-describedby="schedule-blocked">
        {w.scheduleSitting}
      </Button>
      <p id="schedule-blocked" className="text-osce-meta text-b2b-muted">
        {`Nothing can be scheduled until an ${w.exam} is ready. `}
        <Link href={hrefFor(NEW_EXAM_PATH)} className={b2bTokens.b2bLink}>
          {`Set up an ${w.exam}`}
        </Link>
      </p>
    </div>
  );

  const header =
    runs && !mayDecide ? (
      <SupervisorHeader orgSlug={orgSlug} eyebrow={w.Supervisor} />
    ) : w.hiring ? (
      <HireHeader name={data.name} words={w} action={schedules ? scheduleAction : null} />
    ) : (
      <PageHead
        eyebrow={dateEyebrow(new Date())}
        title={todayGreeting(name, new Date())}
        description={todaySentence(running, attention.length)}
        action={schedules ? scheduleAction : null}
      />
    );
  // What is happening now comes before what exists: on an examination morning it is the
  // only thing anybody wants.
  const live = runs ? <LiveNow orgSlug={orgSlug} onCount={setRunning} statusHost={statusHost} /> : null;
  const needs = mayDecide || notJoined ? <NeedsAttention loading={results.loading} error={results.error} items={attention} /> : null;

  const comingUpSection = (
    <BoardSection
      title="Coming up"
      aside={
        <Link href={hrefFor("/sittings")} className={cn(b2bTokens.b2bLink, "text-assess-label")}>
          {`All ${w.sittings}`}
        </Link>
      }
    >
      {upcoming.length === 0 ? (
        <BoardRow>
          <RowText
            title={`No ${w.sittings} are scheduled.`}
            meta={schedules ? <Link href={hrefFor(SCHEDULE_SITTING_PATH)} className={b2bTokens.b2bLink}>{w.scheduleSitting}</Link> : `An administrator can schedule one.`}
          />
        </BoardRow>
      ) : (
        upcoming.map((sitting, index) => <SittingRow key={sitting.id} sitting={sitting} first={index === 0} />)
      )}
    </BoardSection>
  );
  const recent =
    earlier.length > 0 ? (
      <BoardSection title={`Recent ${w.sittings}`}>
        {earlier.map((sitting, index) => (
          <SittingRow key={sitting.id} sitting={sitting} first={index === 0} />
        ))}
      </BoardSection>
    ) : null;
  // A supervisor's own circuits: the board's Supervisor home. Their lists end where the board ends; the org's
  // upcoming sittings and recent ones, and what is running, stay under it.
  const mine = (
    <>
      {runs && circuits.error ? <Alert tone="danger">{errorMessage(circuits.error)}</Alert> : null}
      {runs && circuits.loading ? <Spinner /> : null}
      {runs && !circuits.loading && !circuits.error ? <NextCircuit rows={circuitRows} /> : null}
      {runs ? <StationsToReview orgSlug={orgSlug} /> : null}
      {runs && !circuits.loading && !circuits.error ? <SupervisorCircuits rows={circuitRows} sayWhenEmpty={!admin} /> : null}
    </>
  );
  if (w.hiring && admin) {
    // The hire overview board (HireHome) is the whole screen: header, the running hero, what needs a
    // decision and three counts. The institution's lists of sittings are not drawn under it.
    return (
      <section aria-label="Overview" className={cn(b2bTokens.assessPage, "!w-auto")}>
        {header}
        {live}
        {needs}
        <div ref={setStatusHost} className="empty:hidden" />
        <Counts data={data} upcoming={upcoming.length} />
      </section>
    );
  }
  if (runs && !mayDecide) {
    return (
      <>
        <section aria-label="Supervisor home" className={b2bTokens.assessPage}>
          {header}
          {mine}
        </section>
        <div className={b2bTokens.assessPage}>
          {live}
          {comingUpSection}
          {recent}
        </div>
      </>
    );
  }
  return (
    <>
      <section aria-label="Today" className={b2bTokens.assessPage}>
        {header}
        {live}
        {needs}
        {comingUpSection}
        {admin ? <Counts data={data} setup today /> : null}
      </section>
      <div className={b2bTokens.assessPage}>
        {mine}
        {recent}
      </div>
    </>
  );
}

function SittingRow({ sitting, first }: { sitting: NonNullable<Data["recent_sittings"]>[number]; first: boolean }) {
  const date = dateTile(sitting.scheduled_for);
  const { hrefFor } = useSurface();
  const w = useAssessWords();
  return (
    <BoardRow href={hrefFor(`/sittings/${sitting.id}`)} first={first}>
      {date ? (
        <div aria-hidden className="w-14 text-center">
          <div className={b2bTokens.assessMeta}>{date.month}</div>
          <div className="text-assess-section font-semibold">{date.day}</div>
        </div>
      ) : null}
      <RowText
        title={sitting.name}
        meta={[
          sitting.scheduled_for && !date ? new Date(sitting.scheduled_for).toLocaleString() : null,
          modeLabel(sitting.mode, w),
          sittingTally(sitting, w),
        ]
          .filter(Boolean)
          .join(" · ")}
      />
      <span className={boardChip(sitting.status === "scheduled" ? "info" : "neutral")}>{humanise(sitting.status)}</span>
    </BoardRow>
  );
}

/**
 * Decisions waiting and results ready to release, oldest first, from the results index.
 * Then the server's count of people who have not joined, which opens People.
 */
function NeedsAttention({ loading, error, items }: { loading: boolean; error: unknown; items: AttentionItem[] }) {
  const { hrefFor } = useSurface();
  const hiring = useAssessWords().hiring;
  if (loading) return <Spinner />;
  if (error) return <Alert tone="danger">{errorMessage(error)}</Alert>;
  if (hiring) return <HireAttention items={items} />;

  return (
    <BoardSection title="Needs your attention" aside={<span className={b2bTokens.assessMeta}>Oldest first</span>}>
      {items.length === 0 ? (
        <BoardRow>
          <RowText
            title="Nothing needs you right now."
            meta={
              <Link href={hrefFor("/results")} className={b2bTokens.b2bLink}>
                Open Results
              </Link>
            }
          />
        </BoardRow>
      ) : (
        items.map((item, index) => (
          <BoardRow key={item.key} href={hrefFor(item.href)} first={index === 0}>
            <span className={boardChip(item.tone === "warn" ? "warn" : item.tone === "ok" ? "ok" : "neutral")}>{item.tag}</span>
            <RowText title={item.title} meta={item.body} />
            <RowChevron />
          </BoardRow>
        ))
      )}
    </BoardSection>
  );
}

/**
 * The count tiles: the Today and setup boards' four white cards with a sans number (`setup`, `assessStat*`);
 * the hire overview's three.
 */
function Counts({ data, setup = false, today = false, upcoming }: { data: Data; setup?: boolean; today?: boolean; upcoming?: number }) {
  const w = useAssessWords();
  const { hrefFor } = useSurface();
  const counts = data.counts;

  if (setup) {
    return (
      <section aria-label="At a glance" className="flex flex-wrap gap-4">
        {[
          ...setupTiles(counts, w).map((tile) => (today && tile.path === "/team" ? { ...tile, label: w.Supervisors } : tile)),
          ...(today ? [{ label: w.Sittings, value: counts.sittings, path: "/sittings" }] : []),
        ].map((tile) => (
          <Link key={tile.label} href={hrefFor(tile.path)} className={cn(b2bTokens.assessCard, b2bTokens.assessStat)}>
            <span className={b2bTokens.assessMeta}>{tile.label === "Exams ready" ? "Exams ready to schedule" : tile.label}</span>
            <span className={b2bTokens.assessStatNumber}>{tile.value}</span>
          </Link>
        ))}
      </section>
    );
  }

  const tiles = [
    { label: w.Trainees, value: counts.trainees, path: "/trainees" },
    { label: w.Supervisors, value: counts.staff, path: "/team" },
    upcoming === undefined
      ? { label: w.Sittings, value: counts.sittings, path: "/sittings" }
      : { label: `Upcoming ${w.sittings}`, value: upcoming, path: "/sittings" },
  ];
  return (
    <section aria-label="At a glance" className="grid grid-cols-1 gap-3 min-[901px]:grid-cols-3">
      {tiles.map((tile) => (
        <Link key={tile.label} href={hrefFor(tile.path)} className={cn(b2bTokens.assessCard, "p-4 text-assess-desc !leading-[normal] text-osce-ink-900 hover:bg-osce-canvas")}>
          {tile.label}
          <b className="mt-1 block text-assess-h2 font-semibold !leading-[normal]">{tile.value}</b>
        </Link>
      ))}
    </section>
  );
}
