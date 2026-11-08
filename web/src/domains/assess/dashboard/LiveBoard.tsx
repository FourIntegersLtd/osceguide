"use client";

import { HiOutlineExclamationTriangle } from "react-icons/hi2";
import { AsyncBoundary, Button, b2bTokens, cn } from "@/foundation/ui";
import { boardAlert, boardBtn, boardCardClipped, boardChip, boardHeadRow, boardPad } from "@/foundation/ui/boardKit";
import { useAsync, useCursorPages, useEventStream } from "@/foundation/hooks";
import Link from "next/link";
import { useSurface } from "@/capabilities";
import { can, useSession } from "@/foundation/session";
import { ExamClock } from "@/capabilities/attempt-runner";
import { alertCopy, examStationNumber } from "@/domains/assess/sessions/support";
import {
  liveBoardStreamPath,
  readLiveBoard,
  readLiveHistory,
  type LiveBoard as Board,
  type LiveCircuit,
  type LiveRun,
} from "@/domains/assess/dashboard/api";
import {
  boardOrder,
  candidatesLabel,
  circuitStatus,
  modeLabel,
  recordingMissing,
  runsByDay,
} from "@/domains/assess/dashboard/support";
import { useAssessWords } from "@/capabilities/assess-words";
import { BoardRow, RowText } from "@/domains/assess/dashboard/BoardParts";
import {
  HIRE_LIVE,
  earlierEmptyDescription,
  earlierRunText,
  hireEarlierLabel,
  hireRowChip,
  hireRowName,
  hireRowStation,
  hireWarning,
  liveCardLink,
  liveDescription,
  liveEmptyBody,
  liveEmptyTitle,
  nextSittingLine,
  recordingMissingAdvice,
  runningHeading,
} from "@/domains/assess/dashboard/hireLive";

/**
 * The exam-day board: everything this organisation has running, at once.
 *
 * The screen that did not exist. A course lead on the morning of an OSCE could
 * open one circuit's console, or a list of sittings that did not say which
 * were live, so "how is the morning going" was answered by walking between
 * rooms.
 *
 * Rows are ordered by trouble and then by whoever runs out of time first, so
 * the top of the board is where somebody should be standing.
 */
export function LiveBoard({ orgSlug }: { orgSlug: string }) {
  const initial = useAsync((signal) => readLiveBoard(orgSlug, signal), [orgSlug]);
  const { session } = useSession();
  // Only staff are let into the stream; for anybody else it would read "Reconnecting" for ever.
  const streaming = can(session, "run_circuits");
  const stream = useEventStream<Board>(liveBoardStreamPath(orgSlug), { enabled: streaming });
  const board = stream.data ?? initial.data;
  const { hrefFor } = useSurface();
  const w = useAssessWords();

  return (
    <section aria-label="Now running" className={b2bTokens.assessPage}>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className={b2bTokens.assessEyebrow}>Run</div>
          <h1 className={b2bTokens.assessTitle}>Now running</h1>
          <p className={b2bTokens.assessDesc}>
            {liveDescription(w)}
          </p>
        </div>
        {streaming ? <span className={boardChip(stream.connected ? "ok" : "warn")}>{stream.connected ? "Live" : "Reconnecting"}</span> : null}
      </div>

      {stream.error ? (
        <div role="alert" className={boardAlert("bad")}>
          Live updates stopped. Reload to reconnect.
        </div>
      ) : null}

      <AsyncBoundary state={initial}>
        {() => {
          const circuits = boardOrder(board?.circuits ?? []);
          const next = board?.next_sitting ?? null;
          const nextLine = next ? nextSittingLine(next, w) : null;
          const emptyBody = liveEmptyBody(Boolean(nextLine), w);
          if (circuits.length === 0) {
            return (
              <div className={boardPad}>
                <h2 className="text-assess-desc font-semibold">{liveEmptyTitle(w)}</h2>
                {emptyBody ? <p className={cn(b2bTokens.assessMeta, "m-0")}>{emptyBody}</p> : null}
                {nextLine ? <p className={cn(b2bTokens.assessMeta, "m-0")}>{nextLine}</p> : null}
                {w.hiring ? (
                  <Link href={hrefFor(next ? `/sittings/${next.id}` : "/sittings")} className={cn(boardBtn("primary"), "self-start")}>
                    {next ? HIRE_LIVE.nextLink : HIRE_LIVE.emptyLink}
                  </Link>
                ) : null}
              </div>
            );
          }
          return (
            <>
              {board?.worker_running === false ? (
                <div role="alert" className={boardAlert("warn")}>
                  The background worker is not running. This screen still moves due circuits on, but marking and clearing patients from rooms wait until it is back. Tell your platform admin.
                </div>
              ) : null}
              <section
                aria-label="Live"
                className="box-border flex flex-wrap items-center justify-between gap-5 rounded-panel border border-osce-accent bg-assess-hero-live-bg p-6"
              >
                <div>
                  <div className={b2bTokens.assessEyebrow}>Live</div>
                  <h2 className="mt-1 text-assess-section font-semibold">
                    {runningHeading(circuits.length, w)}
                  </h2>
                  <div className={b2bTokens.assessMeta}>{circuits[0]!.sitting_name}</div>
                </div>
                <Link href={hrefFor(`/circuits/${circuits[0]!.circuit_id}`)} className={boardBtn("primary")}>
                  {liveCardLink(circuits[0]!.circuit_name, w)}
                </Link>
              </section>
              {circuits.map((circuit) => (
                <Notices key={circuit.circuit_id} circuit={circuit} />
              ))}
              <section aria-label="Running" className={boardCardClipped}>
                <div className="flex flex-wrap items-center gap-4 px-5 py-3.5">
                  <h2 className="text-assess-desc font-semibold leading-[1.3]">Running</h2>
                  <span className={b2bTokens.assessMeta}>Trouble first, then least time left</span>
                </div>
                {w.hiring ? (
                  <div className={boardHeadRow}>
                    <span className="flex-[1_1_240px]">{w.Circuit}</span>
                    <span className="w-14">Clock</span>
                  </div>
                ) : null}
                {circuits.map((circuit) => (
                  <Row key={circuit.circuit_id} circuit={circuit} />
                ))}
              </section>
            </>
          );
        }}
      </AsyncBoundary>

      <Earlier orgSlug={orgSlug} />
    </section>
  );
}

const timeOf = (iso: string) =>
  new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });

/**
 * What already ran, newest first: this morning, yesterday, and further back
 * on request.
 *
 * The board above is now only, so once a circuit ended it vanished and "what
 * ran this morning" had no answer short of opening each sitting. Each row
 * opens the circuit's own console, where its record and feedback are.
 */
function Earlier({ orgSlug }: { orgSlug: string }) {
  const w = useAssessWords();
  const { hrefFor } = useSurface();
  const history = useCursorPages(
    (cursor, signal) => readLiveHistory(orgSlug, cursor, signal),
    [orgSlug],
  );

  return (
    <section className="flex flex-col gap-4" aria-label="Earlier">
      <AsyncBoundary
        state={history.state}
        empty={{
          title: "Nothing has finished yet.",
          description: earlierEmptyDescription(w),
        }}
      >
        {(runs: LiveRun[]) => (
          <div className={boardCardClipped}>
            {runsByDay(runs, new Date()).map((group, groupIndex) => (
              <div key={group.label}>
                <div className={cn(w.hiring ? "flex items-center justify-between px-5 py-3.5" : "px-5 py-3.5", groupIndex > 0 && "border-t border-osce-border-light")}>
                  <div className={b2bTokens.assessEyebrow}>{hireEarlierLabel(group.label, w)}</div>
                  {w.hiring ? <div className={b2bTokens.assessEyebrow}>Ended</div> : null}
                </div>
                {group.runs.map((run) => {
                  const when = (
                    <span className={b2bTokens.assessMeta}>
                      {run.started_at ? `${timeOf(run.started_at)}–` : "ended "}
                      {timeOf(run.ended_at)}
                    </span>
                  );
                  const line = earlierRunText(run, modeLabel(run.mode, w), w);
                  const text = <RowText title={line.title} meta={line.meta} />;
                  return run.circuit_id ? (
                    <BoardRow key={run.id} href={hrefFor(`/circuits/${run.circuit_id}`)}>
                      {text}
                      {when}
                    </BoardRow>
                  ) : (
                    <BoardRow key={run.id}>
                      {text}
                      {when}
                    </BoardRow>
                  );
                })}
              </div>
            ))}
            {history.hasMore ? (
              <div className="flex justify-center border-t border-osce-border-light px-5 py-3.5">
                <Button themeType="b2b" variant="ghost" size="sm" disabled={history.loadingMore} onClick={history.loadMore}>
                  {history.loadingMore ? "Loading…" : "Show earlier"}
                </Button>
              </div>
            ) : null}
          </div>
        )}
      </AsyncBoundary>
      {history.moreError ? (
        <div role="alert" className={boardAlert("bad")}>
          Could not load more: {history.moreError.message}
        </div>
      ) : null}
    </section>
  );
}

/** The three stages a station moves through, with the current one filled. */
const STAGES = [
  { phase: "reading", label: "Reading" },
  { phase: "simulation", label: "Consultation" },
  { phase: "break", label: "Between" },
] as const;

function StageStrip({ circuit }: { circuit: LiveCircuit }) {
  const current = STAGES.findIndex((stage) => stage.phase === circuit.phase);
  return (
    <span role="list" className="hidden text-assess-meta text-osce-ink-500 md:inline" aria-label="Stage">
      {STAGES.map((stage, index) => (
        <span key={stage.phase} role="listitem">
          {index > 0 ? " › " : ""}
          <span className={index === current ? "font-semibold text-osce-ink-900" : undefined}>{stage.label}</span>
        </span>
      ))}
    </span>
  );
}

function Row({ circuit }: { circuit: LiveCircuit }) {
  const w = useAssessWords();
  const { hrefFor } = useSurface();
  if (w.hiring) return <HireRow circuit={circuit} />;
  const station = circuit.current_station
    ? `Station ${circuit.current_station.slot_index + 1} of ${circuit.stations_total}${
        circuit.current_station.title ? ` · ${circuit.current_station.title}` : ""
      }`
    : `Between stations · ${circuit.stations_completed} of ${circuit.stations_total} sat`;

  return (
    <BoardRow href={hrefFor(`/circuits/${circuit.circuit_id}`)}>
      <RowText
        title={circuit.circuit_name}
        meta={`${circuit.sitting_name} · ${modeLabel(circuit.mode, w)} · ${station} · ${candidatesLabel(circuit)}${
          circuit.supervisor
            ? ` · ${circuit.supervisor.name ?? circuit.supervisor.email ?? "Supervisor"}`
            : " · no supervisor named"
        }${circuit.room_name ? " · room open" : ""}`}
      />
      <StageStrip circuit={circuit} />
      <span className={boardChip(circuit.paused ? "warn" : "ok")}>{circuitStatus(circuit)}</span>
      {circuit.remaining_seconds !== null && circuit.remaining_seconds !== undefined ? (
        <span className="w-14 text-right font-semibold tabular-nums">
          <ExamClock
            secondsLeft={circuit.remaining_seconds}
            label={circuitStatus(circuit)}
            tick
            paused={circuit.paused}
            plain
          />
        </span>
      ) : null}
    </BoardRow>
  );
}

function Notices({ circuit }: { circuit: LiveCircuit }) {
  const w = useAssessWords();
  const warning = w.hiring ? hireWarning(circuit, new Date()) : null;
  if (w.hiring && warning) {
    return (
      <div role="alert" className={boardAlert("warn")}>
        <span className="inline-flex items-center gap-2">
          <HiOutlineExclamationTriangle className="h-4 w-4 shrink-0" aria-hidden />
          <strong>{warning.title}.</strong> {warning.body}
        </span>
      </div>
    );
  }
  const missing = recordingMissing(circuit);
  const alerts = circuit.alerts ?? [];
  const station = examStationNumber(circuit.mode, circuit.current_station?.slot_index);
  if (!missing && alerts.length === 0) return null;
  return (
    <div className="flex flex-col gap-2">
      {missing ? (
        <div role="alert" className={boardAlert("bad")}>
          <span className="inline-flex items-center gap-2">
            <HiOutlineExclamationTriangle className="h-4 w-4 shrink-0" aria-hidden />
            {circuit.circuit_name}: {station ? `Recording missing for Station ${station}.` : "Recording missing."} {recordingMissingAdvice(w)}
          </span>
        </div>
      ) : null}
      {alerts.map((code) => (
        <div key={code} role="alert" className={boardAlert("warn")}>
          {circuit.circuit_name}: {alertCopy(code, "board", station, circuit.overdue_seconds)}
        </div>
      ))}
    </div>
  );
}

/** An employer's row: the candidate on the rotation, the station, a Live / Not joined / Paused chip and the clock. */
function HireRow({ circuit }: { circuit: LiveCircuit }) {
  const { hrefFor } = useSurface();
  const chip = hireRowChip(circuit);
  return (
    <BoardRow href={hrefFor(`/circuits/${circuit.circuit_id}`)}>
      <RowText title={hireRowName(circuit)} meta={`${circuit.sitting_name} · ${hireRowStation(circuit)}`} />
      <span className={boardChip(chip === "Live" ? "ok" : "warn")}>{chip}</span>
      {circuit.remaining_seconds !== null && circuit.remaining_seconds !== undefined ? (
        <span className="w-14 text-right font-semibold tabular-nums">
          <ExamClock secondsLeft={circuit.remaining_seconds} label={chip} tick paused={circuit.paused} plain />
        </span>
      ) : null}
    </BoardRow>
  );
}
