"use client";

import Link from "next/link";
import { can, useSession } from "@/foundation/session";
import { useState } from "react";
import { useAsync } from "@/foundation/hooks";
import { Alert, AsyncBoundary, ButtonLink } from "@/foundation/ui";
import { assessDesc, assessEyebrow, assessMeta, assessTitle } from "@/foundation/ui/b2bTokens";
import { boardCard, boardRow, boardChip } from "@/foundation/ui/boardKit";
import { useSurface } from "@/capabilities";
import { readCircuitReview, type CircuitConsole } from "@/domains/assess/sessions/api";
import { AddTraineesDialog } from "@/domains/assess/sessions/AddTraineesDialog";
import { CircuitHero } from "@/domains/assess/sessions/CircuitHero";
import { CircuitRecordNote } from "@/domains/assess/sessions/CircuitRecordNote";
import { Rail } from "@/domains/assess/sessions/RailSection";
import { CircuitFeedbackCard } from "@/domains/assess/sessions/CircuitFeedbackCard";
import { InterventionsLog } from "@/domains/assess/sessions/InterventionsLog";
import { ObserverPanel } from "@/domains/assess/sessions/ObserverPanel";
import { closeRoom } from "@/domains/assess/room/api";
import { SupervisorRoom } from "@/domains/assess/room/SupervisorRoom";
import { SplitCard } from "@/domains/assess/room/SplitCard";
import { SidePanel } from "@/domains/assess/room/SidePanel";
import { LiveMarkPanel } from "@/domains/assess/sessions/LiveMarkPanel";
import { RunnerHelpPanel } from "@/domains/assess/sessions/RunnerHelpPanel";
import { StationProgressList } from "@/domains/assess/sessions/StationProgressList";
import { SupervisorReadingBrief } from "@/domains/assess/sessions/SupervisorReadingBrief";
import { TurnStrip } from "@/domains/assess/sessions/TurnStrip";
import { alertCopy, examStationNumber, observerSubtitle, orderedSlots, slotProgress } from "@/domains/assess/sessions/support";
import { useCircuitRun, useObserverRoom } from "@/domains/assess/sessions/useCircuitRun";
import { cardTitle } from "@/domains/assess/chrome";
import { useAssessWords } from "@/capabilities/assess-words";
import { aOrAn } from "@/capabilities/assess-words/vocabulary";
import { HIRE_CONSOLE } from "@/domains/assess/sessions/hireConsole";

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
  const w = useAssessWords();
  const run = useCircuitRun(orgSlug, circuitId);

  return (
    <section aria-label={`${w.Circuit} console`} className="flex w-full min-w-0 flex-col gap-6">
      <AsyncBoundary state={run.initial}>
        {() =>
          run.data ? (
            <Runner run={run} data={run.data} orgSlug={orgSlug} circuitId={circuitId} sittingId={sittingId} />
          ) : null
        }
      </AsyncBoundary>
    </section>
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
  const w = useAssessWords();
  const { hrefFor } = useSurface();
  const { session } = useSession();
  const observer = useObserverRoom(orgSlug, circuitId);
  const [adding, setAdding] = useState(false);
  // One read of the circuit's published feedback, shared by the review step and the feedback card.
  const review = useAsync((signal) => readCircuitReview(orgSlug, circuitId, signal), [orgSlug, circuitId]);
  const circuit = data.circuit;
  const isExam = data.sitting.mode === "exam";
  /** A practice room that is open: one card with the tiles and the marking beside them. */
  const roomLive = !isExam && circuit.started_at !== null && circuit.ended_at === null && !circuit.room_closed_at;
  /** Ended, and the supervisor has not closed the room yet: the room stands alone in its own card. */
  const roomKept = !isExam && circuit.started_at !== null && circuit.ended_at !== null && !circuit.room_closed_at;
  /** A live exam: listening in beside the marking, in one card like the practice room. */
  const examLive = isExam && circuit.started_at !== null && circuit.ended_at === null;
  const room = <SupervisorRoom data={data} orgSlug={orgSlug} circuitId={circuitId} observer={observer} onClose={() => run.run("close-room", () => closeRoom(orgSlug, circuitId))} />;
  const onSlot = orderedSlots(data).find((slot) => ["reading", "in_consultation"].includes(slotProgress(slot)));
  const station = examStationNumber(data.sitting.mode, onSlot?.slot_index);
  const live = circuit.started_at !== null && circuit.ended_at === null;
  // An invited supervisor has no name yet (it arrives empty), so fall back to the address.
  const supervisorName = circuit.supervisor?.name || circuit.supervisor?.email;

  return (
    <>
      <div>
        <Link href={hrefFor(w.hiring ? "" : `/sittings/${sittingId ?? data.sitting.id}`)} className="text-assess-label text-osce-accent">
          {w.hiring ? `‹ ${HIRE_CONSOLE.back}` : `‹ ${data.sitting.name}`}
        </Link>
      </div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className={assessEyebrow}>{w.hiring ? HIRE_CONSOLE.eyebrow : `${w.Circuit} console`}</div>
          <h1 className={assessTitle}>{circuit.name}</h1>
          <p className={assessDesc}>
            {`${observerSubtitle(data)}${supervisorName ? ` · ${w.Supervisor}: ${supervisorName}` : ` · No ${w.supervisor} assigned`}`}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          <RunnerHelpPanel kind={isExam ? "exam" : "training"} />
          {/* Offered only while the circuit's slots can still be rebuilt, which
              is the backend's rule: it sends `editable` with the frame so a
              supervisor is not invited to delete a consultation in progress. */}
          {circuit.editable && can(session, "schedule_sittings") ? (
            <ButtonLink href={hrefFor(`/circuits/${circuitId}/edit`)} themeType="b2b" variant="secondary" size="sm">
              Edit
            </ButtonLink>
          ) : null}
          {/* The stream being up is the difference between a stale screen and
              a live one, so it is said rather than assumed, until the circuit
              ends and the stream closing is expected. */}
          {circuit.ended_at === null ? (
            <span className={boardChip(run.connected ? "ok" : "warn")}>{run.connected ? "Live" : "Reconnecting"}</span>
          ) : (
            <span className={boardChip("neutral")}>Ended</span>
          )}
          {circuit.paused ? <span className={boardChip("warn")}>Paused</span> : null}
        </div>
      </div>

      {/* Alerts arrive as codes on purpose: the board decides how to say it. */}
      {(circuit.alerts ?? []).length > 0 ? (
        <div data-board="alerts" className="flex flex-col gap-3">
          {(circuit.alerts ?? []).map((code) => (
            <Alert key={code} tone="warning">
              {alertCopy(code, "console", station, circuit.overdue_seconds)}
            </Alert>
          ))}
        </div>
      ) : null}

      <CircuitHero
        data={data}
        orgSlug={orgSlug}
        circuitId={circuitId}
        busy={run.busy}
        reconnecting={run.reconnecting}
        failure={run.failure}
        run={run.run}
        onDismissFailure={run.dismissFailure}
        published={review.data?.state === "published"}
        training={!isExam}
      />

      {roomLive || examLive ? (
        <SplitCard
          sideTitle="Marking"
          main={examLive ? <ObserverPanel data={data} observer={observer} /> : room}
          side={
            circuit.active_slot_id ? (
              <LiveMarkPanel orgSlug={orgSlug} circuitId={circuitId} slotId={circuit.active_slot_id} tick={data} peers={!isExam} />
            ) : (
              <SidePanel title="Marking">
                <p className={`${assessMeta} p-4`}>{`Marking opens when ${isExam ? "a candidate" : `${aOrAn(w.trainee)}`} is on.`}</p>
              </SidePanel>
            )
          }
        />
      ) : null}

      <div className="flex flex-wrap items-start gap-6">
        <div className="flex min-w-0 flex-[999_1_520px] flex-col gap-5">
          {roomKept ? <div className={`${boardCard} p-4 sm:p-5`}>{room}</div> : null}
          {!isExam && circuit.ended_at === null ? (
            <TurnStrip
              data={data}
              orgSlug={orgSlug}
              circuitId={circuitId}
              busy={run.busy}
              offline={run.reconnecting}
              failure={run.failure}
              run={run.run}
              onAdd={live ? () => setAdding(true) : undefined}
            />
          ) : null}

          {isExam || circuit.ended_at !== null ? (
            <div id="circuit-review" className={boardCard}>
              <div className={`${boardRow} border-t-0`}>
                <h2 className={cardTitle}>Station progress</h2>
              </div>
              <StationProgressList data={data} agentLive={circuit.agent_dispatched} />
            </div>
          ) : null}

          <SupervisorReadingBrief data={data} orgSlug={orgSlug} />
        </div>

        <div className="flex min-w-0 flex-[1_1_300px] flex-col gap-5">
          <Rail>
            {circuit.ended_at !== null ? <CircuitRecordNote /> : null}
            <CircuitFeedbackCard
              data={data}
              orgSlug={orgSlug}
              circuitId={circuitId}
              review={review}
              busy={run.busy}
              offline={run.reconnecting}
              run={run.run}
            />
            <InterventionsLog orgSlug={orgSlug} circuitId={circuitId} />
          </Rail>
        </div>
      </div>

      {!isExam && adding ? (
        <AddTraineesDialog
          open
          data={data}
          orgSlug={orgSlug}
          circuitId={circuitId}
          busy={run.busy}
          offline={run.reconnecting}
          failure={run.failure}
          run={run.run}
          onClose={() => setAdding(false)}
        />
      ) : null}
    </>
  );
}
