"use client";

import { HiOutlineExclamationTriangle } from "react-icons/hi2";
import { LuClipboardCheck } from "react-icons/lu";
import {
  Alert,
  AsyncBoundary,
  B2CGroupedRow,
  B2CGroupedRowLink,
  B2CGroupedSection,
  B2CHero,
  B2CPageHeader,
  Badge,
  Button,
  ButtonLink,
  EmptyState,
} from "@/foundation/ui";
import { useAsync, useCursorPages, useEventStream } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { can, useSession } from "@/foundation/session";
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
  const { session } = useSession();
  // Only staff are let into the stream; for anybody else it would read "Reconnecting" for ever.
  const streaming = can(session, "run_circuits");
  const stream = useEventStream<Board>(liveBoardStreamPath(orgSlug), { enabled: streaming });
  const board = stream.data ?? initial.data;
  const { hrefFor } = useSurface();

  return (
    <div className="flex w-full min-w-0 flex-col gap-5">
      <B2CPageHeader
        title="Now running"
        subtitle="Every circuit that is live in your organisation, updated as it happens."
        action={
          streaming ? (
            <Badge variant={stream.connected ? "success" : "warning"} dot>
              {stream.connected ? "Live" : "Reconnecting"}
            </Badge>
          ) : null
        }
      />

      {stream.error ? (
        <Alert tone="danger">Live updates stopped. Reload to reconnect.</Alert>
      ) : null}

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
            <div className="flex flex-col gap-3">
              {board?.worker_running === false ? (
                <Alert tone="warning">
                  The background worker is not running. This screen still moves due circuits on, but
                  marking and clearing patients from rooms wait until it is back. Tell your platform
                  admin.
                </Alert>
              ) : null}
              <B2CHero
                eyebrow="Live"
                title={`${circuits.length} ${circuits.length === 1 ? "circuit" : "circuits"} running`}
                action={
                  <ButtonLink
                    href={hrefFor(`/circuits/${circuits[0]!.circuit_id}`)}
                    themeType="b2b"
                    variant="commit"
                  >
                    Open {circuits[0]!.circuit_name}
                  </ButtonLink>
                }
              >
                {circuits[0]!.sitting_name}
              </B2CHero>
              <p className="text-sm text-ink-muted">Trouble first, then least time left.</p>
              <B2CGroupedSection eyebrow="Running">
                {circuits.map((circuit) => (
                  <Row key={circuit.circuit_id} circuit={circuit} />
                ))}
              </B2CGroupedSection>
              {circuits.map((circuit) => (
                <Notices key={circuit.circuit_id} circuit={circuit} />
              ))}
            </div>
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
 * opens the circuit's own console, where its record and feedback are.
 */
function Earlier({ orgSlug }: { orgSlug: string }) {
  const { hrefFor } = useSurface();
  const history = useCursorPages(
    (cursor, signal) => readLiveHistory(orgSlug, cursor, signal),
    [orgSlug],
  );

  return (
    <section className="flex flex-col gap-4" aria-label="Earlier">
      <AsyncBoundary
        state={history.state}
        empty={{ title: "Nothing has finished yet.", description: "Circuits appear here when they end." }}
      >
        {(runs: LiveRun[]) => (
          <>
            {runsByDay(runs, new Date()).map((group) => (
              <B2CGroupedSection key={group.label} eyebrow={`Earlier · ${group.label}`}>
                {group.runs.map((run) => {
                  const rowProps = {
                    title: run.circuit_name,
                    meta: `${run.sitting_name} · ${run.mode} · ${run.candidate_count} ${
                      run.candidate_count === 1 ? "candidate" : "candidates"
                    } · ${run.stations_completed} of ${run.stations_total} stations${
                      run.status === "ended_early" ? " · ended early" : ""
                    }`,
                    trailing: (
                      <span className="shrink-0 font-mono text-osce-meta text-b2b-mid">
                        {run.started_at ? `${timeOf(run.started_at)}–` : "ended "}
                        {timeOf(run.ended_at)}
                      </span>
                    ),
                  };
                  return run.circuit_id ? (
                    <B2CGroupedRowLink
                      key={run.id}
                      href={hrefFor(`/circuits/${run.circuit_id}`)}
                      icon={LuClipboardCheck}
                      {...rowProps}
                    />
                  ) : (
                    <B2CGroupedRow key={run.id} icon={LuClipboardCheck} {...rowProps} />
                  );
                })}
              </B2CGroupedSection>
            ))}
          </>
        )}
      </AsyncBoundary>
      {history.moreError ? (
        <Alert tone="danger">Could not load more: {history.moreError.message}</Alert>
      ) : null}
      {history.hasMore ? (
        <Button
          themeType="b2b"
          variant="ghost"
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

/** The three stages a station moves through, with the current one filled. */
const STAGES = [
  { phase: "reading", label: "Reading" },
  { phase: "simulation", label: "Consultation" },
  { phase: "break", label: "Between" },
] as const;

function StageStrip({ circuit }: { circuit: LiveCircuit }) {
  const current = STAGES.findIndex((stage) => stage.phase === circuit.phase);
  return (
    <ol className="hidden items-center gap-2 md:flex" aria-label="Stage">
      {STAGES.map((stage, index) => (
        <li key={stage.phase} className="flex items-center gap-2">
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              index === current ? "bg-b2b-headline" : index < current ? "bg-b2b-mid" : "bg-b2b-border"
            }`}
            aria-hidden
          />
          <span
            className={`text-osce-meta ${index === current ? "text-b2b-headline" : "text-b2b-mid"}`}
          >
            {stage.label}
          </span>
        </li>
      ))}
    </ol>
  );
}

function Row({ circuit }: { circuit: LiveCircuit }) {
  const { hrefFor } = useSurface();
  const station = circuit.current_station
    ? `Station ${circuit.current_station.slot_index + 1} of ${circuit.stations_total}${
        circuit.current_station.title ? ` · ${circuit.current_station.title}` : ""
      }`
    : `Between stations · ${circuit.stations_completed} of ${circuit.stations_total} sat`;

  return (
    <B2CGroupedRowLink
      href={hrefFor(`/circuits/${circuit.circuit_id}`)}
      icon={LuClipboardCheck}
      title={circuit.circuit_name}
      meta={`${circuit.sitting_name} · ${circuit.mode} · ${station} · ${candidatesLabel(circuit)}${
        circuit.supervisor
          ? ` · ${circuit.supervisor.name ?? circuit.supervisor.email ?? "Supervisor"}`
          : " · no supervisor named"
      }${circuit.room_name ? " · room open" : ""}`}
      trailing={
        <div className="flex shrink-0 items-center gap-3">
          <StageStrip circuit={circuit} />
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
      }
    />
  );
}

function Notices({ circuit }: { circuit: LiveCircuit }) {
  const missing = recordingMissing(circuit);
  const alerts = circuit.alerts ?? [];
  if (!missing && alerts.length === 0) return null;
  return (
    <div className="flex flex-col gap-2">
      {missing ? (
        <Alert tone="danger">
          <span className="inline-flex items-center gap-2">
            <HiOutlineExclamationTriangle className="h-4 w-4 shrink-0" aria-hidden />
            {circuit.circuit_name}: a consultation is running but is not being recorded. Open the circuit and send the patient in again.
          </span>
        </Alert>
      ) : null}
      {alerts.map((code) => (
        <Alert key={code} tone="warning">
          {circuit.circuit_name}: {alertCopy(code)}
        </Alert>
      ))}
    </div>
  );
}
