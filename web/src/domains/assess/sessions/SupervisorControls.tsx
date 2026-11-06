"use client";

import { useState } from "react";
import { Alert, Button, ButtonLink } from "@/foundation/ui";
import { can, useSession } from "@/foundation/session";
import { assessMeta } from "@/foundation/ui/b2bTokens";
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
  const canMark = can(session, "sign_off_results");
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
      <>
        {canMark ? (
          <>
            <p className={assessMeta}>Its stations can still be marked and its record read.</p>
            <ButtonLink href="#circuit-review" themeType="b2b" variant="secondary" className="self-start">
              Mark a finished station
            </ButtonLink>
          </>
        ) : null}
      </>
    );
  }

  return (
    <div className="flex flex-col gap-3.5">
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

      {started ? null : (
        <p className={assessMeta}>
          Starting begins reading time for station 1. Every override asks for a reason, kept with the record.
        </p>
      )}

      <div className="flex flex-wrap items-center gap-2.5">
        {!started ? (
          <Button
            themeType="b2b"
            variant="commit"
            isLoading={busy === "start"}
            disabled={working}
            onClick={() => run("start", () => runControls.start(orgSlug, circuitId))}
          >
            Start circuit
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
              Next station
            </Button>

            <Button
              themeType="b2b"
              variant="secondary"
              disabled={working}
              onClick={() =>
                openRequest(circuit.paused ? resumeRequest(orgSlug, circuitId) : pauseRequest(orgSlug, circuitId))
              }
            >
              {circuit.paused ? "Resume" : "Pause"}
            </Button>

            <Button
              themeType="b2b"
              variant="secondary"
              disabled={working}
              onClick={() => openRequest(extendRequest(orgSlug, circuitId))}
            >
              Extend the clock
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
            >Resend the
              patient
            </Button>

            <Button
              themeType="b2b"
              variant="danger"
              disabled={working}
              onClick={() => openRequest(endRequest(orgSlug, circuitId))}
            >End circuit
            </Button>
          </>
        )}
      </div>

      {started ? (
        <label className="flex min-h-8 items-start gap-2.5 text-assess-label text-osce-ink-900">
          <input
            type="checkbox"
            checked={circuit.auto_advance}
            disabled={working}
            onChange={(event) =>
              void run("auto-advance", () =>
                setAutoAdvance(orgSlug, circuitId, event.target.checked),
              )
            }
            className="mt-0.5 h-[18px] w-[18px]"
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
