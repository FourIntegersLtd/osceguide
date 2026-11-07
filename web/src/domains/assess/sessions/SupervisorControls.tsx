"use client";

import { useState } from "react";
import { ActionMenu, Alert, Button } from "@/foundation/ui";
import { assessMeta } from "@/foundation/ui/b2bTokens";
import { overrides, runControls, setAutoAdvance } from "@/domains/assess/sessions/api";
import type { CircuitConsole } from "@/domains/assess/sessions/api";
import { primaryTurnAction } from "@/domains/assess/sessions/turns";
import { OverrideDialog, type OverrideRequest } from "@/domains/assess/sessions/OverrideDialog";
import type { AssessWords } from "@/domains/assess/vocabulary";
import { useAssessWords } from "@/domains/assess/useAssessWords";

/**
 * The controls a supervisor runs an examination from.
 *
 * One inline primary (start, or next station) and Pause/Resume, which must be one tap in a live
 * exam. Extend, reset, resend and end sit in the "⋯" menu, end last. Pause and the menu's actions
 * are a human stepping in and are asked for a reason, which the backend keeps beside the action.
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
  training = false,
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
  /** A training circuit: the primary brings in the next trainee. */
  training?: boolean;
}) {
  const w = useAssessWords();
  const [request, setRequest] = useState<OverrideRequest | null>(null);
  // A new dialog must not open on the last action's failure.
  const openRequest = (next: OverrideRequest) => {
    onDismissFailure();
    setRequest(next);
  };
  const closeRequest = () => setRequest(null);
  const circuit = data.circuit;
  const started = circuit.started_at !== null;
  const turn = primaryTurnAction(data);
  const working = busy !== null || reconnecting;
  // Shown under a disabled menu item, and read out as its reason.
  const waitHint = working ? (reconnecting ? `Reconnecting to the ${w.circuit}` : "Another action is running") : undefined;

  async function commit(input: { reason: string | null; seconds: number }) {
    if (!request) return;
    const pending = request;
    await run(pending.name, () => pending.run(input));
    closeRequest();
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
          Pausing, adding time or skipping asks for a reason. {`It is saved with the ${w.circuit}.`}
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
            {`Start ${w.circuit}`}
          </Button>
        ) : (
          <>
            <Button
              themeType="b2b"
              variant="commit"
              isLoading={busy === "advance"}
              disabled={working}
              onClick={() =>
                training && turn.kind === "end"
                  ? openRequest(endRequest(orgSlug, circuitId, w))
                  : run("advance", () => runControls.advance(orgSlug, circuitId))
              }
            >
              {training ? turn.label : "Next station"}
            </Button>

            <Button
              themeType="b2b"
              variant="secondary"
              disabled={working}
              onClick={() =>
                openRequest(circuit.paused ? resumeRequest(orgSlug, circuitId, w) : pauseRequest(orgSlug, circuitId, w))
              }
            >
              {circuit.paused ? "Resume" : "Pause"}
            </Button>

            <ActionMenu
              label={`More ${w.circuit} controls`}
              items={[
                { label: "Add time", disabled: working, hint: waitHint, onSelect: () => openRequest(extendRequest(orgSlug, circuitId)) },
                { label: "Restart the timer", disabled: working, hint: waitHint, onSelect: () => openRequest(resetRequest(orgSlug, circuitId)) },
                { label: "Resend the patient", disabled: working, hint: waitHint, onSelect: () => openRequest(resendRequest(orgSlug, circuitId)) },
                ...(training && turn.kind === "end"
                  ? []
                  : [{ label: `End ${w.circuit}`, tone: "danger" as const, disabled: working, hint: waitHint, onSelect: () => openRequest(endRequest(orgSlug, circuitId, w)) }]),
              ]}
            />
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
          Move on by itself when time is up. If off, you press {training ? `the button above to bring in the next ${w.trainee}` : "Next station"}.
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

function pauseRequest(slug: string, circuitId: string, w: AssessWords): OverrideRequest {
  return {
    name: "pause",
    title: `Pause the ${w.circuit}`,
    lead: "The clock stops for everybody. The patient stays in the room.",
    commitLabel: "Pause",
    run: ({ reason }) => overrides.pause(slug, circuitId, reason),
  };
}

function resumeRequest(slug: string, circuitId: string, w: AssessWords): OverrideRequest {
  return {
    name: "resume",
    title: `Resume the ${w.circuit}`,
    lead: "The clock starts again where it stopped.",
    commitLabel: "Resume",
    run: ({ reason }) => overrides.resume(slug, circuitId, reason),
  };
}

function extendRequest(slug: string, circuitId: string): OverrideRequest {
  return {
    name: "extend",
    title: "Add time",
    lead: "Adds time to the part running now. Later stations are not changed.",
    commitLabel: "Add time",
    seconds: 60,
    run: ({ reason, seconds }) => overrides.extendClock(slug, circuitId, seconds, reason),
  };
}

function resetRequest(slug: string, circuitId: string): OverrideRequest {
  return {
    name: "reset",
    title: "Restart the timer",
    lead: "Restarts the part running now from the beginning.",
    commitLabel: "Restart",
    run: ({ reason }) => overrides.resetClock(slug, circuitId, reason),
  };
}

function resendRequest(slug: string, circuitId: string): OverrideRequest {
  return {
    name: "resend",
    title: "Resend the patient",
    lead: "Brings the patient back in. The candidate starts the consultation again.",
    commitLabel: "Resend",
    run: ({ reason }) => overrides.resendPatient(slug, circuitId, reason),
  };
}

function endRequest(slug: string, circuitId: string, w: AssessWords): OverrideRequest {
  return {
    name: "end",
    title: `End the ${w.circuit}`,
    lead: "Any station nobody has taken is marked as skipped. You cannot undo this. End it only when everyone has finished.",
    commitLabel: `End the ${w.circuit}`,
    tone: "danger",
    run: ({ reason }) => runControls.end(slug, circuitId, reason),
  };
}
