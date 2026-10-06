"use client";

import Link from "next/link";
import { useState } from "react";
import { HiOutlineUserPlus } from "react-icons/hi2";
import { Alert, AsyncBoundary, B2CPageHeader, Badge, Button, b2bTokens } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { ExamClock } from "@/capabilities/attempt-runner";
import type { CircuitConsole } from "@/domains/assess/sessions/api";
import { AddTraineesDialog } from "@/domains/assess/sessions/AddTraineesDialog";
import { CircuitFeedbackCard } from "@/domains/assess/sessions/CircuitFeedbackCard";
import { InterventionsLog } from "@/domains/assess/sessions/InterventionsLog";
import { LiveMarkingSidebar } from "@/domains/assess/sessions/LiveMarkingSidebar";
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
  // An invited supervisor has no name yet (it arrives empty), so fall back to the address.
  const supervisorName = circuit.supervisor?.name || circuit.supervisor?.email;

  return (
    <>
      <B2CPageHeader
        back={{ href: hrefFor(`/sittings/${sittingId ?? data.sitting.id}`), label: data.sitting.name }}
        title={circuit.name}
        subtitle={`${observerSubtitle(data)}${
          supervisorName ? ` · Supervisor: ${supervisorName}` : " · No supervisor assigned"
        }`}
        action={
          <div className="flex flex-wrap items-center gap-2">
            <RunnerHelpPanel kind={isExam ? "exam" : "training"} />
            {/* Offered only while the circuit's slots can still be rebuilt, which
                is the backend's rule: it sends `editable` with the frame so a
                supervisor is not invited to delete a consultation in progress. */}
            {circuit.editable ? (
              <Link href={hrefFor(`/circuits/${circuitId}/edit`)} className={b2bTokens.b2bLink}>
                Edit
              </Link>
            ) : null}
            {/* The stream being up is the difference between a stale screen and
                a live one, so it is said rather than assumed, until the circuit
                ends and the stream closing is expected. */}
            {circuit.ended_at === null ? (
              <Badge variant={run.connected ? "success" : "warning"} dot>
                {run.connected ? "Live" : "Reconnecting"}
              </Badge>
            ) : (
              <Badge variant="neutral">Ended</Badge>
            )}
            {circuit.paused ? <Badge variant="warning">Paused</Badge> : null}
            {!isExam && live ? (
              <Button themeType="b2b" variant="secondary" size="sm" onClick={() => setAdding(true)}>
                <HiOutlineUserPlus className="h-4 w-4 shrink-0" aria-hidden /> Add trainee
              </Button>
            ) : null}
          </div>
        }
      />

      {/* Alerts arrive as codes on purpose: the board decides how to say it. */}
      {(circuit.alerts ?? []).map((code) => (
        <Alert key={code} tone="warning">
          {alertCopy(code)}
        </Alert>
      ))}

      <section className="grid grid-cols-1 gap-6 rounded-panel bg-canvas p-5 sm:p-6 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
        <div className="min-w-0 space-y-5">
          <RunnerStepper steps={runnerSteps(data)} />
          <SupervisorControls
            data={data}
            orgSlug={orgSlug}
            circuitId={circuitId}
            busy={run.busy}
            failure={run.failure}
            run={run.run}
            onDismissFailure={run.dismissFailure}
          />
        </div>
        {/* The clock is the server's: ExamClock only interpolates between pushes. */}
        {circuit.remaining_seconds !== null && circuit.remaining_seconds !== undefined ? (
          <div className="lg:text-right">
            <ExamClock
              secondsLeft={circuit.remaining_seconds}
              label={phaseLabel(circuit.phase)}
              tick
              paused={circuit.paused}
              className="flex-col !items-start gap-1 border-0 bg-transparent px-0 py-0 lg:!items-end [&>span:first-child]:text-osce-body [&>span:first-child]:normal-case [&>span:first-child]:tracking-normal [&>span:last-child]:text-[56px] [&>span:last-child]:leading-none"
            />
            <p className="mt-1 text-osce-meta text-b2b-mid">Server clock</p>
          </div>
        ) : null}
      </section>

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
        <h2 className={b2bTokens.b2bSectionTitle}>Station progress</h2>
        <StationProgressList data={data} agentLive={circuit.agent_dispatched} />
      </section>

      <SupervisorReadingBrief data={data} orgSlug={orgSlug} />

      <ObserverPanel data={data} observer={observer} />

      <LiveMarkingSidebar data={data} orgSlug={orgSlug} />

      <CircuitFeedbackCard
        data={data}
        orgSlug={orgSlug}
        circuitId={circuitId}
        busy={run.busy}
        run={run.run}
      />

      <InterventionsLog orgSlug={orgSlug} circuitId={circuitId} />

      {!isExam && adding ? (
        <AddTraineesDialog
          open
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
