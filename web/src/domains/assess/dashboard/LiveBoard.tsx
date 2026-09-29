"use client";

import Link from "next/link";
import { useState } from "react";
import { HiMiniSignal, HiOutlineExclamationTriangle } from "react-icons/hi2";
import { Alert, AsyncBoundary, Badge, EmptyState, b2bTokens } from "@/foundation/ui";
import { useAsync, useEventStream } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { ExamClock } from "@/capabilities/attempt-runner";
import { alertCopy } from "@/domains/assess/sessions/support";
import {
  liveBoardStreamPath,
  readCircuitsOnDay,
  readLiveBoard,
  type LiveBoard as Board,
  type LiveCircuit,
} from "@/domains/assess/dashboard/api";
import {
  boardOrder,
  candidatesLabel,
  circuitStatus,
  localDay,
  recordingMissing,
  type PastCircuit,
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
 * What ran on a day: this morning by default, any day on request.
 *
 * The board above is now only, so once a circuit ended it vanished and "what
 * ran this morning" had no answer short of opening each sitting. Each row
 * opens the circuit's own console, where its record and feedback are.
 */
function Earlier({ orgSlug }: { orgSlug: string }) {
  const { hrefFor } = useSurface();
  const [day, setDay] = useState(() => localDay(new Date()));
  const today = localDay(new Date());
  const past = useAsync((signal) => readCircuitsOnDay(orgSlug, day, signal), [orgSlug, day]);

  return (
    <section className="space-y-3 border-t border-b2b-border pt-5" aria-labelledby="live-earlier">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 id="live-earlier" className={b2bTokens.b2bSectionTitle}>
          {day === today ? "Earlier today" : "On this day"}
        </h2>
        <div className="flex items-center gap-2">
          <label htmlFor="live-earlier-day" className="text-osce-caption text-b2b-mid">
            Day
          </label>
          <input
            id="live-earlier-day"
            type="date"
            value={day}
            max={today}
            onChange={(event) => {
              if (event.target.value) setDay(event.target.value);
            }}
            className={b2bTokens.b2bInputBase}
          />
        </div>
      </div>
      <AsyncBoundary
        state={past}
        empty={{
          title: day === today ? "Nothing has run yet today." : "Nothing ran that day.",
        }}
      >
        {(rows: PastCircuit[]) => (
          <ul className="divide-y divide-b2b-border rounded-lg border border-b2b-border bg-white">
            {rows.map((row) => (
              <li
                key={row.circuitId}
                className="flex flex-wrap items-center justify-between gap-3 px-4 py-3"
              >
                <div className="min-w-0">
                  <Link
                    href={hrefFor(`/circuits/${row.circuitId}`)}
                    className="text-osce-body font-semibold text-b2b-headline hover:underline"
                  >
                    {row.circuitName}
                  </Link>
                  <p className="mt-0.5 text-osce-caption text-b2b-mid">
                    {row.sittingName} · {row.mode} · {row.stations}{" "}
                    {row.stations === 1 ? "station" : "stations"}
                  </p>
                </div>
                <span className="shrink-0 font-mono text-osce-caption text-b2b-mid">
                  {row.endedAt
                    ? `${timeOf(row.startedAt)}–${timeOf(row.endedAt)}`
                    : `since ${timeOf(row.startedAt)}`}
                </span>
              </li>
            ))}
          </ul>
        )}
      </AsyncBoundary>
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
            A consultation is running and nothing is recording it. Open the circuit and resend the
            patient.
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
