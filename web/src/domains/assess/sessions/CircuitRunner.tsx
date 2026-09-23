"use client";

import Link from "next/link";
import { useState } from "react";
import { HiOutlineUserPlus } from "react-icons/hi2";
import { Alert, AsyncBoundary, Badge, Button, b2bTokens } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { ExamClock } from "@/capabilities/attempt-runner";
import type { CircuitConsole } from "@/domains/assess/sessions/api";
import { AddTraineesDialog } from "@/domains/assess/sessions/AddTraineesDialog";
import { CircuitFeedbackCard } from "@/domains/assess/sessions/CircuitFeedbackCard";
import { InterventionsLog } from "@/domains/assess/sessions/InterventionsLog";
import { ObserverPanel } from "@/domains/assess/sessions/ObserverPanel";
import { RunnerHelpPanel } from "@/domains/assess/sessions/RunnerHelpPanel";
import { RunnerStepper } from "@/domains/assess/sessions/RunnerStepper";
import { StationProgressList } from "@/domains/assess/sessions/StationProgressList";
import { SupervisorControls } from "@/domains/assess/sessions/SupervisorControls";
import { SupervisorReadingBrief } from "@/domains/assess/sessions/SupervisorReadingBrief";
import { TurnStrip } from "@/domains/assess/sessions/TurnStrip";
import { alertCopy, observerSubtitle, phaseLabel, runnerSteps } from "@/domains/assess/sessions/support";
import { useCircuitRun, useObserverRoom } from "@/domains/assess/sessions/useCircuitRun";

/**
 * The screen an examination is run from.
 *
 * One layout for both modes, because they turned out to be the same screen: a
 * training circuit is several people rotating through stations and an
 * examination is one candidate walking them, and either way the circuit runs
 * itself and a supervisor watches it. What differs is the turn strip — there
 * is nobody to rotate in an examination — and who may be added to it.
 *
 * The retiring runner was two layouts over ninety-four files, with the clock
 * in the supervisor's browser and each of them deriving its own answer to
 * "where are we". Everything below reads one console frame.
 */
export function CircuitRunner({
  orgSlug,
  circuitId,
  sittingId,
}: {
  orgSlug: string;
  circuitId: string;
  /** Known from the route when there is one; the frame carries it otherwise. */
  sittingId?: string;
}) {
  const run = useCircuitRun(orgSlug, circuitId);

  return (
    <div className="flex w-full min-w-0 flex-col gap-5">
      <AsyncBoundary state={run.initial}>
        {() =>
          run.data ? (
            <Runner run={run} data={run.data} orgSlug={orgSlug} circuitId={circuitId} sittingId={sittingId} />
          ) : null
        }
      </AsyncBoundary>
    </div>
  );
}

function Runner({
  run,
  data,
  orgSlug,
  circuitId,
  sittingId,
}: {
  run: ReturnType<typeof useCircuitRun>;
  data: CircuitConsole;
  orgSlug: string;
  circuitId: string;
  sittingId?: string;
}) {
  const { hrefFor } = useSurface();
  const observer = useObserverRoom(orgSlug, circuitId);
  const [adding, setAdding] = useState(false);
  const circuit = data.circuit;
  const isExam = data.sitting.mode === "exam";
  const live = circuit.started_at !== null && circuit.ended_at === null;
  const supervisor = circuit.supervisor;

  return (
    <>
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-b2b-border pb-4">
        <div className="min-w-0">
          <Link
            href={hrefFor(`/sittings/${sittingId ?? data.sitting.id}`)}
            className={b2bTokens.b2bLinkMuted}
          >
            ← {data.sitting.name}
          </Link>
          <h1 className={`mt-1 ${b2bTokens.b2bPageTitle}`}>{circuit.name}</h1>
          <p className="mt-1 text-osce-caption text-b2b-mid">
            {observerSubtitle(data)}
            {supervisor
              ? ` · Supervisor: ${supervisor.name ?? supervisor.email ?? "assigned"}`
              : ""}
          </p>
        </div>

        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <RunnerHelpPanel kind={isExam ? "exam" : "training"} />
          {/*
            Offered only while the circuit's slots can still be rebuilt, which
            is the backend's rule and not this screen's guess — it sends
            `editable` with the frame precisely so a supervisor is not invited to
            delete a consultation in progress. Once anything on the circuit means
            something the link is gone rather than there and refusing.
          */}
          {circuit.editable ? (
            <Link href={hrefFor(`/circuits/${circuitId}/edit`)} className={b2bTokens.b2bLink}>
              Edit
            </Link>
          ) : null}
          {/* The stream being up is the difference between a stale screen and
              a live one, so it is said rather than assumed — until the circuit
              ends, when the stream closing is the expected thing and a
              "Reconnecting" badge would be warning about nothing. */}
          {circuit.ended_at === null ? (
            <Badge variant={run.connected ? "success" : "warning"} dot>
              {run.connected ? "Live" : "Reconnecting"}
            </Badge>
          ) : (
            <Badge variant="neutral">Ended</Badge>
          )}
          {circuit.paused ? <Badge variant="warning">Paused</Badge> : null}
          {circuit.remaining_seconds !== null && circuit.remaining_seconds !== undefined ? (
            <ExamClock
              secondsLeft={circuit.remaining_seconds}
              label={phaseLabel(circuit.phase)}
            />
          ) : null}
          {!isExam && live ? (
            <Button themeType="b2b" variant="secondary" size="sm" onClick={() => setAdding(true)}>
              <HiOutlineUserPlus className="h-4 w-4 shrink-0" aria-hidden /> Add trainee
            </Button>
          ) : null}
        </div>
      </header>

      {/* Alerts arrive as codes on purpose: the board decides how to say it. */}
      {(circuit.alerts ?? []).map((code) => (
        <Alert key={code} tone="warning">
          {alertCopy(code)}
        </Alert>
      ))}

      <section className="rounded-lg border border-b2b-border bg-white p-4 sm:p-5">
        <RunnerStepper steps={runnerSteps(data)} />
      </section>

      <SupervisorControls
        data={data}
        orgSlug={orgSlug}
        circuitId={circuitId}
        busy={run.busy}
        failure={run.failure}
        run={run.run}
        onDismissFailure={run.dismissFailure}
      />

      {!isExam ? (
        <TurnStrip
          data={data}
          orgSlug={orgSlug}
          circuitId={circuitId}
          busy={run.busy}
          failure={run.failure}
          run={run.run}
        />
      ) : null}

      <section className="space-y-2">
        <h2 className={b2bTokens.b2bEyebrow}>Station progress</h2>
        <StationProgressList data={data} agentLive={circuit.agent_dispatched} />
      </section>

      <SupervisorReadingBrief data={data} orgSlug={orgSlug} />

      <ObserverPanel data={data} observer={observer} />

      <CircuitFeedbackCard
        data={data}
        orgSlug={orgSlug}
        circuitId={circuitId}
        busy={run.busy}
        run={run.run}
      />

      <InterventionsLog orgSlug={orgSlug} circuitId={circuitId} />

      {!isExam ? (
        <AddTraineesDialog
          open={adding}
          data={data}
          orgSlug={orgSlug}
          circuitId={circuitId}
          busy={run.busy}
          failure={run.failure}
          run={run.run}
          onClose={() => setAdding(false)}
        />
      ) : null}
    </>
  );
}
