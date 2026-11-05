"use client";

import { useState } from "react";
import {
  HiArrowPathRoundedSquare,
  HiChevronDoubleRight,
  HiOutlineClock,
  HiPause,
  HiPlay,
  HiStop,
} from "react-icons/hi2";
import { Alert, Button } from "@/foundation/ui";
import { can, useSession } from "@/foundation/session";
import { overrides, runControls, setAutoAdvance } from "@/domains/assess/sessions/api";
import type { CircuitConsole } from "@/domains/assess/sessions/api";
import { OverrideDialog, type OverrideRequest } from "@/domains/assess/sessions/OverrideDialog";

/**
 * The controls a supervisor runs an examination from.
 *
 * Two kinds of button, kept visibly apart. Start, next station and end are the
 * examination running; pause, extend, reset and resend are a human stepping in
 * and are asked for a reason, which the backend keeps beside the action.
 */
export function SupervisorControls({
  data,
  orgSlug,
  circuitId,
  busy,
  reconnecting,
  failure,
  run,
  onDismissFailure,
}: {
  data: CircuitConsole;
  orgSlug: string;
  circuitId: string;
  busy: string | null;
  /** The stream is down: nothing is offered that would act on a stale screen. */
  reconnecting: boolean;
  failure: string | null;
  run: (name: string, action: () => Promise<unknown>) => Promise<void>;
  onDismissFailure: () => void;
}) {
  const { session } = useSession();
  const [request, setRequest] = useState<OverrideRequest | null>(null);
  // A new dialog must not open on the last action's failure.
  const openRequest = (next: OverrideRequest) => {
    onDismissFailure();
    setRequest(next);
  };
  const closeRequest = () => setRequest(null);
  const circuit = data.circuit;
  const started = circuit.started_at !== null;
  const ended = circuit.ended_at !== null;
  const working = busy !== null || reconnecting;

  async function commit(input: { reason: string | null; seconds: number }) {
    if (!request) return;
    const pending = request;
    await run(pending.name, () => pending.run(input));
    closeRequest();
  }

  if (ended) {
    return (
      <div className="rounded-panel border border-b2b-border bg-canvas/40 px-4 py-3">
        <p className="text-osce-body text-b2b-mid">
          This circuit has ended.
          {can(session, "sign_off_results") ? " Its stations can still be marked and its record read." : ""}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {failure ? (
        <Alert tone="danger">
          <span className="flex flex-wrap items-center justify-between gap-2">
            {failure}
            <button
              type="button"
              onClick={onDismissFailure}
              className="shrink-0 underline underline-offset-2"
            >
              Dismiss
            </button>
          </span>
        </Alert>
      ) : null}

      <div className="flex flex-wrap items-center gap-2">
        {!started ? (
          <Button
            themeType="b2b"
            variant="commit"
            isLoading={busy === "start"}
            disabled={working}
            onClick={() => run("start", () => runControls.start(orgSlug, circuitId))}
          >
            <HiPlay className="h-4 w-4 shrink-0" aria-hidden /> Start circuit
          </Button>
        ) : (
          <>
            <Button
              themeType="b2b"
              variant="commit"
              isLoading={busy === "advance"}
              disabled={working}
              onClick={() => run("advance", () => runControls.advance(orgSlug, circuitId))}
            >
              <HiChevronDoubleRight className="h-4 w-4 shrink-0" aria-hidden /> Next station
            </Button>

            <Button
              themeType="b2b"
              variant="secondary"
              disabled={working}
              onClick={() =>
                openRequest(circuit.paused ? resumeRequest(orgSlug, circuitId) : pauseRequest(orgSlug, circuitId))
              }
            >
              {circuit.paused ? (
                <HiPlay className="h-4 w-4 shrink-0" aria-hidden />
              ) : (
                <HiPause className="h-4 w-4 shrink-0" aria-hidden />
              )}
              {circuit.paused ? "Resume" : "Pause"}
            </Button>

            <Button
              themeType="b2b"
              variant="secondary"
              disabled={working}
              onClick={() => openRequest(extendRequest(orgSlug, circuitId))}
            >
              <HiOutlineClock className="h-4 w-4 shrink-0" aria-hidden /> Extend the clock
            </Button>

            <Button
              themeType="b2b"
              variant="secondary"
              disabled={working}
              onClick={() => openRequest(resetRequest(orgSlug, circuitId))}
            >
              Reset the clock
            </Button>

            <Button
              themeType="b2b"
              variant="secondary"
              disabled={working}
              onClick={() => openRequest(resendRequest(orgSlug, circuitId))}
            >
              <HiArrowPathRoundedSquare className="h-4 w-4 shrink-0" aria-hidden /> Resend the
              patient
            </Button>

            <Button
              themeType="b2b"
              variant="danger"
              disabled={working}
              onClick={() => openRequest(endRequest(orgSlug, circuitId))}
            >
              <HiStop className="h-4 w-4 shrink-0" aria-hidden /> End circuit
            </Button>
          </>
        )}
      </div>

      {started ? null : (
        <p className="text-osce-caption text-b2b-mid">
          Not started yet? One button: Start circuit. Every override asks for a reason, kept with the record.
          {" "}Starting begins reading time for station 1.
        </p>
      )}

      {started ? (
        <label className="flex items-center gap-2 text-osce-caption text-b2b-mid">
          <input
            type="checkbox"
            checked={circuit.auto_advance}
            disabled={working}
            onChange={(event) =>
              void run("auto-advance", () =>
                setAutoAdvance(orgSlug, circuitId, event.target.checked),
              )
            }
            className="h-4 w-4 rounded border-b2b-border text-b2b-accent"
          />
          Moves to the next station automatically when time is up. When off, the circuit waits for you before each new station.
        </label>
      ) : null}

      <OverrideDialog
        request={request}
        busy={working}
        error={failure}
        onClose={closeRequest}
        onCommit={(input) => void commit(input)}
      />
    </div>
  );
}

function pauseRequest(slug: string, circuitId: string): OverrideRequest {
  return {
    name: "pause",
    title: "Pause the circuit",
    lead: "The clock stops for everybody. The patient stays in the room.",
    commitLabel: "Pause",
    run: ({ reason }) => overrides.pause(slug, circuitId, reason),
  };
}

function resumeRequest(slug: string, circuitId: string): OverrideRequest {
  return {
    name: "resume",
    title: "Resume the circuit",
    lead: "The clock starts again from where it stopped.",
    commitLabel: "Resume",
    run: ({ reason }) => overrides.resume(slug, circuitId, reason),
  };
}

function extendRequest(slug: string, circuitId: string): OverrideRequest {
  return {
    name: "extend",
    title: "Extend the clock",
    lead: "Adds time to the phase that is running now, for this station only.",
    commitLabel: "Add the time",
    seconds: 60,
    run: ({ reason, seconds }) => overrides.extendClock(slug, circuitId, seconds, reason),
  };
}

function resetRequest(slug: string, circuitId: string): OverrideRequest {
  return {
    name: "reset",
    title: "Reset the clock",
    lead: "Restarts the phase that is running now from its full duration.",
    commitLabel: "Reset it",
    run: ({ reason }) => overrides.resetClock(slug, circuitId, reason),
  };
}

function resendRequest(slug: string, circuitId: string): OverrideRequest {
  return {
    name: "resend",
    title: "Resend the patient",
    lead: "Dispatches a new patient to the station that is running. The consultation starts over for this candidate.",
    commitLabel: "Resend",
    run: ({ reason }) => overrides.resendPatient(slug, circuitId, reason),
  };
}

function endRequest(slug: string, circuitId: string): OverrideRequest {
  return {
    name: "end",
    title: "End the circuit",
    lead: "Stations nobody has sat are recorded as skipped. This cannot be undone.",
    commitLabel: "End the circuit",
    tone: "danger",
    run: ({ reason }) => runControls.end(slug, circuitId, reason),
  };
}
