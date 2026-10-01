"use client";

import Link from "next/link";
import { HiMiniSignal, HiOutlineExclamationTriangle } from "react-icons/hi2";
import { Alert, AsyncBoundary, Badge, Button, EmptyState, b2bTokens } from "@/foundation/ui";
import { useAsync, useCursorPages, useEventStream } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { ExamClock } from "@/capabilities/attempt-runner";
import { alertCopy } from "@/domains/assess/sessions/support";
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
  recordingMissing,
  runsByDay,
} from "@/domains/assess/dashboard/support";

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
  const stream = useEventStream<Board>(liveBoardStreamPath(orgSlug));
  const board = stream.data ?? initial.data;

  return (
    <div className="flex w-full min-w-0 flex-col gap-5">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-b2b-border pb-4">
        <div className="min-w-0">
          <h1 className={b2bTokens.b2bPageTitle}>Now running</h1>
          <p className="mt-1 text-osce-caption text-b2b-mid">
            Every examination this organisation has in progress.
          </p>
        </div>
        <Badge variant={stream.connected ? "success" : "warning"} dot>
          {stream.connected ? "Live" : "Reconnecting"}
        </Badge>
      </header>

      <AsyncBoundary state={initial}>
        {() => {
          const circuits = boardOrder(board?.circuits ?? []);
          if (circuits.length === 0) {
            return (
              <EmptyState
                title="Nothing is running."
                description="Circuits appear here the moment a supervisor starts one."
              />
            );
          }
          return (
            <ul className="flex flex-col gap-3">
              {circuits.map((circuit) => (
                <li key={circuit.circuit_id}>
                  <Row circuit={circuit} />
                </li>
              ))}
            </ul>
          );
        }}
      </AsyncBoundary>

      <Earlier orgSlug={orgSlug} />
    </div>
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
 * opens the circuit's own console, where its record and feedback are, unless
 * the circuit has since been deleted.
 */
function Earlier({ orgSlug }: { orgSlug: string }) {
  const { hrefFor } = useSurface();
  const history = useCursorPages(
    (cursor, signal) => readLiveHistory(orgSlug, cursor, signal),
    [orgSlug],
  );

  return (
    <section className="space-y-3 border-t border-b2b-border pt-5" aria-labelledby="live-earlier">
      <h2 id="live-earlier" className={b2bTokens.b2bSectionTitle}>
        Earlier
      </h2>
      <AsyncBoundary
        state={history.state}
        empty={{ title: "Nothing has finished yet.", description: "Circuits appear here when they end." }}
      >
        {(runs: LiveRun[]) => (
          <div className="space-y-4">
            {runsByDay(runs, new Date()).map((group) => (
              <div key={group.label} className="space-y-2">
                <h3 className={b2bTokens.b2bEyebrow}>{group.label}</h3>
                <ul className="divide-y divide-b2b-border rounded-lg border border-b2b-border bg-white">
                  {group.runs.map((run) => (
                    <li
                      key={run.id}
                      className="flex flex-wrap items-center justify-between gap-3 px-4 py-3"
                    >
                      <div className="min-w-0">
                        {run.circuit_id ? (
                          <Link
                            href={hrefFor(`/circuits/${run.circuit_id}`)}
                            className="text-osce-body font-semibold text-b2b-headline hover:underline"
                          >
                            {run.circuit_name}
                          </Link>
                        ) : (
                          <span className="text-osce-body font-semibold text-b2b-headline">
                            {run.circuit_name}
                          </span>
                        )}
                        <p className="mt-0.5 text-osce-caption text-b2b-mid">
                          {run.sitting_name} · {run.mode} · {run.candidate_count}{" "}
                          {run.candidate_count === 1 ? "candidate" : "candidates"} ·{" "}
                          {run.stations_completed} of {run.stations_total} stations
                          {run.status === "ended_early" ? " · ended early" : ""}
                        </p>
                      </div>
                      <span className="shrink-0 font-mono text-osce-caption text-b2b-mid">
                        {run.started_at ? `${timeOf(run.started_at)}–` : "ended "}
                        {timeOf(run.ended_at)}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
      </AsyncBoundary>
      {history.moreError ? (
        <Alert tone="danger">Could not load more: {history.moreError.message}</Alert>
      ) : null}
      {history.hasMore ? (
        <Button
          themeType="b2b"
          variant="secondary"
          size="sm"
          disabled={history.loadingMore}
          onClick={history.loadMore}
        >
          {history.loadingMore ? "Loading…" : "Show earlier"}
        </Button>
      ) : null}
    </section>
  );
}

function Row({ circuit }: { circuit: LiveCircuit }) {
  const { hrefFor } = useSurface();
  const missing = recordingMissing(circuit);
  const alerts = circuit.alerts ?? [];

  return (
    <article className="space-y-3 rounded-lg border border-b2b-border bg-white p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <Link
            href={hrefFor(`/circuits/${circuit.circuit_id}`)}
            className="text-osce-body font-semibold text-b2b-headline hover:underline"
          >
            {circuit.circuit_name}
          </Link>
          <p className="mt-0.5 text-osce-caption text-b2b-mid">
            {circuit.sitting_name} · {circuit.mode}
            {circuit.supervisor
              ? ` · ${circuit.supervisor.name ?? circuit.supervisor.email ?? "Supervisor"}`
              : " · no supervisor named"}
          </p>
        </div>

        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <Badge variant={circuit.paused ? "warning" : "success"} dot>
            {circuitStatus(circuit)}
          </Badge>
          {circuit.remaining_seconds !== null && circuit.remaining_seconds !== undefined ? (
            <ExamClock
              secondsLeft={circuit.remaining_seconds}
              label={circuitStatus(circuit)}
              tick
              paused={circuit.paused}
            />
          ) : null}
        </div>
      </div>

      <dl className="flex flex-wrap gap-x-6 gap-y-1 text-osce-caption text-b2b-mid">
        <div className="flex gap-1.5">
          <dt className="font-medium text-b2b-headline">Station</dt>
          <dd>
            {circuit.current_station
              ? `${circuit.current_station.slot_index + 1} of ${circuit.stations_total}${
                  circuit.current_station.title ? ` · ${circuit.current_station.title}` : ""
                }`
              : `between stations · ${circuit.stations_completed} of ${circuit.stations_total} sat`}
          </dd>
        </div>
        <div className="flex gap-1.5">
          <dt className="font-medium text-b2b-headline">Who</dt>
          <dd>{candidatesLabel(circuit)}</dd>
        </div>
        {circuit.room_name ? (
          <div className="flex gap-1.5">
            <dt className="font-medium text-b2b-headline">Room</dt>
            <dd className="inline-flex items-center gap-1">
              <HiMiniSignal className="h-3 w-3 shrink-0 text-b2b-success-icon" aria-hidden />
              open
            </dd>
          </div>
        ) : null}
      </dl>

      {missing ? (
        <Alert tone="danger">
          <span className="inline-flex items-center gap-2">
            <HiOutlineExclamationTriangle className="h-4 w-4 shrink-0" aria-hidden />
            A consultation is running but is not being recorded. Open the circuit and send the patient in again.
          </span>
        </Alert>
      ) : null}

      {alerts.map((code) => (
        <Alert key={code} tone="warning">
          {alertCopy(code)}
        </Alert>
      ))}
    </article>
  );
}
