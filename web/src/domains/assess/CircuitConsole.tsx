"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { LuChevronRight, LuCirclePause, LuCirclePlay, LuRefreshCw, LuSquare } from "react-icons/lu";
import { Alert, AsyncBoundary, Badge, Button, Card, PageHeader, Spinner, cn } from "@/foundation/ui";
import { errorMessage, useAsync, useEventStream } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { ExamClock } from "@/capabilities/attempt-runner";
import {
  circuitActions,
  extendClock,
  readConsole,
  type CircuitConsole as ConsoleData,
  type ConsoleSlot,
} from "@/domains/assess/api";

/**
 * The supervisor's view of a running circuit.
 *
 * The clock is the server's: `remaining_seconds` and `phase_ends_at` come down
 * the stream, so a refresh, a second supervisor or a closed laptop changes
 * nothing about the exam's timing. The old console kept it in one browser and
 * broadcast it over LiveKit data packets, which meant whoever opened the page
 * last could silently restart the station.
 */
export function CircuitConsole({ orgSlug, circuitId }: { orgSlug: string; circuitId: string }) {
  const initial = useAsync((signal) => readConsole(orgSlug, circuitId, signal), [orgSlug, circuitId]);
  const stream = useEventStream<ConsoleData>(
    `/api/v1/orgs/${encodeURIComponent(orgSlug)}/circuits/${encodeURIComponent(circuitId)}/console/stream`,
  );

  // The stream is the truth once it is up; the fetch is what fills the screen
  // before the first frame arrives.
  const data = stream.data ?? initial.data;

  return (
    <div className="flex flex-col gap-5">
      <AsyncBoundary state={initial}>
        {() =>
          data ? (
            <Console
              data={data}
              orgSlug={orgSlug}
              circuitId={circuitId}
              connected={stream.connected}
              onChanged={initial.reload}
            />
          ) : null
        }
      </AsyncBoundary>
    </div>
  );
}

function Console({
  data,
  orgSlug,
  circuitId,
  connected,
  onChanged,
}: {
  data: ConsoleData;
  orgSlug: string;
  circuitId: string;
  connected: boolean;
  onChanged: () => void;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const circuit = data.circuit;

  const run = useCallback(
    async (name: string, action: () => Promise<void>) => {
      setBusy(name);
      setError(null);
      try {
        await action();
        onChanged();
      } catch (cause) {
        setError(cause instanceof Error ? cause : new Error(String(cause)));
      } finally {
        setBusy(null);
      }
    },
    [onChanged],
  );

  const notStarted = circuit.started_at === null;
  const ended = circuit.ended_at !== null;

  return (
    <>
      <PageHeader
        title={circuit.name}
        description={`${data.sitting.name} · ${data.sitting.mode}`}
        actions={
          <div className="flex items-center gap-2">
            <Badge tone={connected ? "success" : "warning"}>
              {connected ? "Live" : "Reconnecting"}
            </Badge>
            {circuit.remaining_seconds !== null && circuit.remaining_seconds !== undefined && (
              <ExamClock
                secondsLeft={circuit.remaining_seconds}
                label={circuit.phase ?? "Station"}
              />
            )}
          </div>
        }
      />

      {error && <Alert tone="danger">{errorMessage(error)}</Alert>}
      {(circuit.alerts ?? []).map((alert) => (
        <Alert key={alert} tone="warning">
          {alert}
        </Alert>
      ))}

      <Card>
        <div className="flex flex-wrap items-center gap-2">
          {notStarted && !ended && (
            <Button
              onClick={() => run("start", () => circuitActions.start(orgSlug, circuitId))}
              disabled={busy !== null}
            >
              {busy === "start" ? <Spinner /> : <LuCirclePlay className="h-4 w-4" aria-hidden />}
              Start circuit
            </Button>
          )}

          {!notStarted && !ended && (
            <>
              <Button
                onClick={() => run("advance", () => circuitActions.advance(orgSlug, circuitId))}
                disabled={busy !== null}
              >
                <LuChevronRight className="h-4 w-4" aria-hidden /> Next station
              </Button>
              <Button
                variant="secondary"
                onClick={() =>
                  run(
                    "pause",
                    () =>
                      circuit.paused
                        ? circuitActions.resume(orgSlug, circuitId)
                        : circuitActions.pause(orgSlug, circuitId),
                  )
                }
                disabled={busy !== null}
              >
                {circuit.paused ? (
                  <LuCirclePlay className="h-4 w-4" aria-hidden />
                ) : (
                  <LuCirclePause className="h-4 w-4" aria-hidden />
                )}
                {circuit.paused ? "Resume" : "Pause"}
              </Button>
              <Button
                variant="secondary"
                onClick={() => run("extend", () => extendClock(orgSlug, circuitId, 60))}
                disabled={busy !== null}
              >
                +1 minute
              </Button>
              <Button
                variant="secondary"
                onClick={() =>
                  run("resend", () => circuitActions.resendPatient(orgSlug, circuitId))
                }
                disabled={busy !== null}
              >
                <LuRefreshCw className="h-4 w-4" aria-hidden /> Resend patient
              </Button>
              <Button
                variant="danger"
                onClick={() => run("end", () => circuitActions.end(orgSlug, circuitId))}
                disabled={busy !== null}
              >
                <LuSquare className="h-4 w-4" aria-hidden /> End circuit
              </Button>
            </>
          )}

          {ended && <p className="text-sm text-ink-muted">This circuit has ended.</p>}
        </div>
      </Card>

      <Card title="Stations" description={`${(data.slots ?? []).length} slots`}>
        <ul className="divide-y divide-border">
          {(data.slots ?? [])
            .slice()
            .sort((a, b) => a.slot_index - b.slot_index)
            .map((slot) => (
              <SlotRow key={slot.id} slot={slot} />
            ))}
        </ul>
      </Card>
    </>
  );
}

function SlotRow({ slot }: { slot: ConsoleSlot }) {
  const { hrefFor } = useSurface();
  // Marking opens once there is something to mark. Offering it before the
  // station has run is how a reviewer ends up filling in a rubric for a
  // consultation nobody had.
  const markable = slot.started_at !== null;
  const reviewHref = hrefFor(
    `/slots/${slot.id}/review${slot.attempt_id ? `?attempt=${slot.attempt_id}` : ""}`,
  );

  return (
    <li
      className={cn(
        "flex flex-wrap items-center justify-between gap-3 px-1 py-3",
        slot.is_active && "bg-accent-subtle",
      )}
    >
      <div className="flex min-w-0 items-center gap-3">
        <span className="w-6 shrink-0 text-center text-xs font-medium text-ink-subtle">
          {slot.slot_index + 1}
        </span>
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-ink">
            {slot.trainee.name ?? slot.trainee.email ?? "Trainee"}
          </p>
          <p className="truncate text-xs text-ink-subtle">{slot.station.title ?? "Station"}</p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        {slot.has_review && <Badge tone="accent">Marked</Badge>}
        <Badge tone={statusTone(slot.status)}>{slot.status}</Badge>
        {markable && (
          <Link
            href={reviewHref}
            className="rounded-control border border-border-strong px-2.5 py-1 text-sm text-ink hover:bg-surface-raised"
          >
            {slot.has_review ? "Review" : "Mark"}
          </Link>
        )}
      </div>
    </li>
  );
}

function statusTone(status: string): "success" | "warning" | "neutral" {
  if (status === "completed" || status === "ended") return "success";
  if (status === "live" || status === "in_progress") return "warning";
  return "neutral";
}
