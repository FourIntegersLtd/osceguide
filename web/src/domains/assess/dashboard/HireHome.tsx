"use client";

import Link from "next/link";
import { useState } from "react";
import { Alert, Badge, Button, Spinner, b2bTokens, cn } from "@/foundation/ui";
import { boardBtn, boardCard, boardChip } from "@/foundation/ui/boardKit";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { ExamClock } from "@/capabilities/attempt-runner";
import { useAssessWords } from "@/capabilities/assess-words";
import { BoardRow, BoardSection, RowChevron, RowText } from "@/domains/assess/dashboard/BoardParts";
import { LiveNow } from "@/domains/assess/dashboard/LiveNow";
import { readSupervisorCircuits, type LiveCircuit, type OrgDashboard as Data } from "@/domains/assess/dashboard/api";
import { hireRail, hireRailNext } from "@/domains/assess/dashboard/setupSteps";
import { attentionFromResults, circuitStatus, comingUp, laterToday, longWhen, notJoinedItem, recordingMissing, runningLine, type AttentionItem } from "@/domains/assess/dashboard/support";
import { readResultsIndex } from "@/domains/assess/results/api";
import { useStationsToReview } from "@/domains/assess/results/StationsToReview";
import { slotReviewPath } from "@/domains/assess/sessions/support";

/** One hero: an eyebrow, the title, a line and the screen's one primary action. */
function Hero({ eyebrow, title, line, action }: { eyebrow: string; title: string; line?: string | null; action: { label: string; href: string } | null; tone?: "live" }) {
  const { hrefFor } = useSurface();
  return (
    <section aria-label={eyebrow} className={cn(boardCard, "flex flex-wrap items-center gap-5 p-6")}>
      <div className="min-w-0 flex-[1_1_320px]">
        <div className={b2bTokens.assessEyebrow}>{eyebrow}</div>
        <h2 className="mb-1 mt-1.5 text-assess-section font-semibold">{title}</h2>
        {line ? <div className={b2bTokens.assessMeta}>{line}</div> : null}
      </div>
      {action ? (
        <Link href={hrefFor(action.href)} className={boardBtn("primary")}>
          {action.label}
        </Link>
      ) : null}
    </section>
  );
}

/** The running circuit's phase, server clock and console link: real controls under the Running now hero. */
function RunningStatus({ circuit }: { circuit: LiveCircuit }) {
  const { hrefFor } = useSurface();
  const status = circuitStatus(circuit);
  const needsALook = recordingMissing(circuit) || (circuit.alerts ?? []).length > 0;
  return (
    <div role="group" aria-label="Running now status" className="flex flex-wrap items-center gap-2.5">
      <Badge variant={needsALook ? "danger" : circuit.paused ? "warning" : "success"} dot>
        {needsALook ? "Needs a look" : circuit.paused ? status : status === "Running" ? "Live" : `Live · ${status}`}
      </Badge>
      {circuit.remaining_seconds !== null && circuit.remaining_seconds !== undefined ? (
        <ExamClock secondsLeft={circuit.remaining_seconds} label={status} tick paused={circuit.paused} />
      ) : null}
      <Link href={hrefFor(`/circuits/${circuit.circuit_id}`)} className={boardBtn()}>
        Open console
      </Link>
    </div>
  );
}

function PageHead({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    <div>
      <div className={b2bTokens.assessEyebrow}>{eyebrow}</div>
      <h1 className={b2bTokens.assessTitle}>{title}</h1>
      <p className={b2bTokens.assessDesc}>{description}</p>
    </div>
  );
}

/**
 * The hire Overview (HireHome, HireAssessorHome). An administrator sees the four-step rail until a first
 * assessment can run, then a busy day (Running now, Needs you) or a quiet one; an assessor sees only their own
 * rotations and stations to mark. Hiring decisions, the Candidates list and Settings are never drawn for an assessor.
 */
export function HireHome({ data, orgSlug, admin }: { data: Data; orgSlug: string; admin: boolean }) {
  const w = useAssessWords();
  const rail = hireRail(data.setup, w);
  if (admin && hireRailNext(rail)) return <NewAccount name={data.name} steps={rail} />;
  return admin ? <AdminDay data={data} orgSlug={orgSlug} /> : <AssessorDay data={data} orgSlug={orgSlug} />;
}

function NewAccount({ name, steps }: { name: string; steps: ReturnType<typeof hireRail> }) {
  const w = useAssessWords();
  const { hrefFor } = useSurface();
  const next = hireRailNext(steps);
  return (
    <div className={b2bTokens.assessPage}>
      <PageHead eyebrow={name} title={w.Home} description={`Four steps to your first ${w.sitting}. Come back to any of them.`} />
      <ol aria-label="Steps" className={cn(boardCard, "flex flex-col")}>
        {steps.map((step, index) => (
          <li key={step.id} aria-current={step === next ? "step" : undefined} className="flex flex-wrap items-center gap-3 border-t border-osce-border-light px-5 py-4 first:border-t-0">
            <span aria-hidden className={step.done ? b2bTokens.assessDotDone : step === next ? b2bTokens.assessDotCurrent : b2bTokens.assessDotIdle}>
              {step.done ? "✓" : index + 1}
            </span>
            <span className="flex-1 font-medium">{step.label}</span>
            {step.optional ? <span className={b2bTokens.assessMeta}>Optional</span> : null}
            {step.done ? <span className={boardChip("ok")}>Done</span> : null}
          </li>
        ))}
      </ol>
      {next ? (
        <div className="flex flex-col items-start gap-1.5">
          {next.blocked ? (
            <Button themeType="b2b" variant="commit" disabled aria-describedby="rail-blocked">
              {next.cta}
            </Button>
          ) : (
            <Link href={hrefFor(next.href)} className={boardBtn("primary")}>
              {next.cta}
            </Link>
          )}
          {next.blocked ? (
            <p id="rail-blocked" className={b2bTokens.assessMeta}>
              {`${next.blocked} `}
              <Link href={hrefFor(steps[0]?.href ?? "/")} className={b2bTokens.b2bLink}>{`Set up an ${w.exam}`}</Link>
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function AdminDay({ data, orgSlug }: { data: Data; orgSlug: string }) {
  const w = useAssessWords();
  const { hrefFor } = useSurface();
  const { session } = useSession();
  const mayDecide = can(session, "sign_off_results");
  const runs = can(session, "run_circuits");
  const [live, setLive] = useState<LiveCircuit | null>(null);
  const results = useAsync((signal) => (mayDecide ? readResultsIndex(orgSlug, signal) : Promise.resolve(null)), [orgSlug, mayDecide]);
  const review = useStationsToReview(runs ? orgSlug : null);
  const notJoined = notJoinedItem(data.counts.invited_not_joined, w);
  const needs: AttentionItem[] = [...attentionFromResults(results.data?.rows ?? [], w), ...(notJoined ? [notJoined] : [])];
  const upcoming = comingUp(data.recent_sittings ?? []);
  const next = upcoming[0];
  const marks = review.stations.length;
  const tiles = [
    { label: w.Trainees, value: data.counts.trainees, path: "/trainees" },
    { label: w.Supervisors, value: data.counts.staff, path: "/team" },
    { label: `Upcoming ${w.sittings}`, value: upcoming.length, path: "/sittings" },
  ];
  return (
    <div className={b2bTokens.assessPage}>
      <PageHead eyebrow={data.name} title={w.Home} description={`Your ${w.sittings}, ${w.trainees} and results.`} />
      {runs ? <LiveNow orgSlug={orgSlug} bare onFirst={setLive} /> : null}
      {live ? (
        <Hero eyebrow="Running now" title={live.sitting_name} line={runningLine(live, w)} action={{ label: w.liveBoardLink, href: "/live" }} />
      ) : next ? (
        <Hero eyebrow={`Next ${w.sitting}`} title={next.name} line={longWhen(next.scheduled_for) ?? "No date set yet."} action={{ label: `Open ${w.sitting}`, href: `/sittings/${next.id}` }} />
      ) : (
        <Hero eyebrow="Nothing is running" title={`No ${w.sittings} are scheduled`} line={`Choose an ${w.exam}, a date and the ${w.trainees}. The ${w.circuits} build themselves.`} action={{ label: w.scheduleSitting, href: "/sittings/new" }} />
      )}
      {live ? <RunningStatus circuit={live} /> : null}
      {results.loading ? <Spinner /> : results.error ? <Alert tone="danger">{errorMessage(results.error)}</Alert> : null}
      {needs.length > 0 || marks > 0 ? (
        <BoardSection title="Needs you">
          {marks > 0 && review.stations[0] ? (
            <BoardRow href={hrefFor(slotReviewPath(review.stations[0]))} first>
              <RowText title={`${marks} ${marks === 1 ? "station" : "stations"} to mark`} meta="Check each AI mark. Your mark is the one that counts." />
              <span className={boardChip("warn")}>To mark</span>
              <RowChevron />
            </BoardRow>
          ) : null}
          {needs.map((item, index) => (
            <BoardRow key={item.key} href={hrefFor(item.href)} first={index === 0 && marks === 0}>
              <RowText title={item.title} meta={item.body} />
              <span className={boardChip(item.tone === "warn" ? "warn" : "neutral")}>{item.tag}</span>
              <RowChevron />
            </BoardRow>
          ))}
        </BoardSection>
      ) : null}
      <section aria-label="At a glance" className="grid grid-cols-1 gap-3 min-[901px]:grid-cols-3">
        {tiles.map((tile) => (
          <Link key={tile.label} href={hrefFor(tile.path)} className={cn(b2bTokens.assessCard, "p-4 text-assess-desc !leading-[normal] text-osce-ink-900 hover:bg-osce-canvas")}>
            {tile.label}
            <b className="mt-1 block text-assess-h2 font-semibold !leading-[normal]">{tile.value}</b>
          </Link>
        ))}
      </section>
    </div>
  );
}

function AssessorDay({ data, orgSlug }: { data: Data; orgSlug: string }) {
  const w = useAssessWords();
  const { hrefFor } = useSurface();
  const circuits = useAsync((signal) => readSupervisorCircuits(orgSlug, signal), [orgSlug]);
  const review = useStationsToReview(orgSlug);
  if (circuits.loading) return <Spinner />;
  if (circuits.error) return <Alert tone="danger">{errorMessage(circuits.error)}</Alert>;
  const rows = (circuits.data?.items ?? []).filter((row) => !row.ended).sort((a, b) => Number(b.in_progress) - Number(a.in_progress));
  const first = rows[0];
  const marks = review.stations.length;
  const later = laterToday(rows, new Date());
  return (
    <div className={b2bTokens.assessPage}>
      <PageHead eyebrow={data.name} title={w.Home} description={`The ${w.circuits} you run and the stations you mark.`} />
      {first ? (
        <Hero
          eyebrow={`Your next ${w.circuit}`}
          title={`${first.circuit_name} · ${first.sitting_name}`}
          line={[longWhen(first.scheduled_for), `${first.slot_count} ${first.slot_count === 1 ? "station" : "stations"}`].filter(Boolean).join(" · ")}
          action={{ label: "Open the console", href: `/circuits/${first.circuit_id}` }}
        />
      ) : null}
      {later.length > 0 ? (
        <BoardSection title="Later today">
          {later.map((row, index) => (
            <BoardRow key={row.circuit_id} href={hrefFor(`/circuits/${row.circuit_id}`)} first={index === 0}>
              <RowText title={row.circuit_name} meta={longWhen(row.scheduled_for)} />
              <RowChevron />
            </BoardRow>
          ))}
        </BoardSection>
      ) : null}
      {marks > 0 && review.stations[0] ? (
        <Hero
          eyebrow="To mark"
          title={`${marks} ${marks === 1 ? "station is" : "stations are"} waiting for your mark`}
          line="Results stay hidden from candidates until the administrator releases them."
          action={{ label: marks === 1 ? "Mark it" : "Mark the first one", href: slotReviewPath(review.stations[0]) }}
        />
      ) : null}
      {!first && marks === 0 ? (
        <section aria-label="Nothing assigned" className={cn(boardCard, "p-6")}>
          <h2 className="text-assess-section font-semibold">Nothing assigned to you</h2>
          <p className={b2bTokens.assessMeta}>{`When an administrator puts you on a ${w.circuit}, it shows here and you get an email.`}</p>
        </section>
      ) : null}
    </div>
  );
}
