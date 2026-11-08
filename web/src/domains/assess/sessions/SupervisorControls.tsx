"use client";

import { useState } from "react";
import { circuitCopy } from "@/domains/assess/sessions/hireConsole";
import { ActionMenu, Alert, Button } from "@/foundation/ui";
import { useAssessWords } from "@/capabilities/assess-words";
import type { AssessWords } from "@/capabilities/assess-words/vocabulary";
import { HIRE_CONSOLE, HIRE_JUMP_DIALOG, hireAutoAdvance, hireRedoDialog, jumpChoices } from "@/domains/assess/sessions/hireConsole";
import { assessMeta } from "@/foundation/ui/b2bTokens";
import { overrides, runControls, setAutoAdvance } from "@/domains/assess/sessions/api";
import type { CircuitConsole, ConsoleSlot } from "@/domains/assess/sessions/api";
import { orderedSlots, stationLabel } from "@/domains/assess/sessions/support";
import { primaryTurnAction } from "@/domains/assess/sessions/turns";
import { OverrideDialog, type OverrideInput, type OverrideRequest } from "@/domains/assess/sessions/OverrideDialog";

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
  const hire = w.hiring;
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

  const RESEND = {
    label: "Resend the patient",
    group: hire ? HIRE_CONSOLE.groups.patient : undefined,
    disabled: working,
    hint: waitHint,
    onSelect: () => openRequest(resendRequest(orgSlug, circuitId)),
  };

  // Redo acts on the station running now; Jump offers every other one.
  const slots = orderedSlots(data);
  const activeSlot = slots.find((slot) => slot.id === circuit.active_slot_id);
  const otherSlots = jumpChoices(data);

  async function copyObserverLink() {
    try {
      await navigator.clipboard.writeText(window.location.href);
    } catch {
      // Clipboard refused: the address bar still holds the link.
    }
  }

  async function commit(input: OverrideInput) {
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
          Pausing, adding time or skipping asks for a reason. It is saved with the circuit.
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
            {hire ? HIRE_CONSOLE.start : "Start circuit"}
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
                  ? openRequest(endRequest(orgSlug, circuitId, hire, w))
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
              label={hire ? HIRE_CONSOLE.menu : "More circuit controls"}
              items={[
                ...(hire ? [RESEND] : []),
                { label: hire ? HIRE_CONSOLE.addTime : "Add time", group: hire ? HIRE_CONSOLE.groups.time : undefined, disabled: working, hint: waitHint, onSelect: () => openRequest(extendRequest(orgSlug, circuitId, hire)) },
                { label: hire ? HIRE_CONSOLE.restartClock : "Restart the timer", group: hire ? HIRE_CONSOLE.groups.time : undefined, disabled: working, hint: waitHint, onSelect: () => openRequest(resetRequest(orgSlug, circuitId)) },
                ...(hire ? [] : [RESEND]),
                ...(hire
                  ? [
                      {
                        label: HIRE_CONSOLE.redo,
                        group: HIRE_CONSOLE.groups.redo,
                        disabled: working || !activeSlot,
                        hint: waitHint ?? (activeSlot ? undefined : HIRE_CONSOLE.noStationRunning),
                        onSelect: () => activeSlot && openRequest(redoRequest(orgSlug, circuitId, activeSlot)),
                      },
                      {
                        label: HIRE_CONSOLE.jump,
                        group: HIRE_CONSOLE.groups.jump,
                        disabled: working || otherSlots.length === 0,
                        hint: waitHint ?? (otherSlots.length === 0 ? HIRE_CONSOLE.noOtherStation : undefined),
                        onSelect: () => openRequest(jumpRequest(orgSlug, circuitId, otherSlots)),
                      },
                    ]
                  : []),
                ...(hire
                  ? [{ label: HIRE_CONSOLE.observerLink, group: HIRE_CONSOLE.groups.watch, onSelect: () => void copyObserverLink() }]
                  : []),
                ...(training && turn.kind === "end"
                  ? []
                  : [{ label: hire ? HIRE_CONSOLE.end : "End circuit", group: hire ? HIRE_CONSOLE.groups.stop : undefined, tone: "danger" as const, disabled: working, hint: waitHint, onSelect: () => openRequest(endRequest(orgSlug, circuitId, hire, w)) }]),
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
          {hire ? hireAutoAdvance(circuit.auto_advance) : `Move on by itself when time is up. If off, you press ${training ? "the button above to bring in the next trainee" : "Next station"}.`}
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
    title: circuitCopy("Pause", w),
    lead: "The clock stops for everybody. The patient stays in the room.",
    commitLabel: "Pause",
    run: ({ reason }) => overrides.pause(slug, circuitId, reason),
  };
}

function resumeRequest(slug: string, circuitId: string, w: AssessWords): OverrideRequest {
  return {
    name: "resume",
    title: circuitCopy("Resume", w),
    lead: "The clock starts again where it stopped.",
    commitLabel: "Resume",
    run: ({ reason }) => overrides.resume(slug, circuitId, reason),
  };
}

function extendRequest(slug: string, circuitId: string, hire = false): OverrideRequest {
  return {
    name: "extend",
    title: hire ? HIRE_CONSOLE.addTime : "Add time",
    lead: "Adds time to the part running now. Later stations are not changed.",
    commitLabel: hire ? HIRE_CONSOLE.addTime : "Add time",
    seconds: hire ? HIRE_CONSOLE.addSeconds : 60,
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

function endRequest(slug: string, circuitId: string, hire: boolean, w: AssessWords): OverrideRequest {
  return {
    name: "end",
    title: hire ? HIRE_CONSOLE.endTitle : circuitCopy("End", w),
    lead: "Any station nobody has taken is marked as skipped. You cannot undo this. End it only when everyone has finished.",
    commitLabel: hire ? HIRE_CONSOLE.endTitle : circuitCopy("End", w),
    tone: "danger",
    run: ({ reason }) => runControls.end(slug, circuitId, reason),
  };
}

function redoRequest(slug: string, circuitId: string, slot: ConsoleSlot): OverrideRequest {
  const copy = hireRedoDialog(stationLabel(slot));
  return {
    name: "redo",
    title: copy.title,
    lead: copy.lead,
    commitLabel: HIRE_CONSOLE.redo,
    run: ({ reason }) => overrides.redoStation(slug, circuitId, slot.id, reason),
  };
}

function jumpRequest(slug: string, circuitId: string, slots: ConsoleSlot[]): OverrideRequest {
  return {
    name: "jump",
    title: HIRE_JUMP_DIALOG.title,
    lead: HIRE_JUMP_DIALOG.lead,
    commitLabel: HIRE_JUMP_DIALOG.commit,
    choiceLabel: HIRE_JUMP_DIALOG.choiceLabel,
    choices: slots.map((slot) => ({ value: slot.id, label: `${slot.slot_index + 1} ${stationLabel(slot)}` })),
    run: ({ reason, choice }) => overrides.jumpTo(slug, circuitId, choice, reason),
  };
}
