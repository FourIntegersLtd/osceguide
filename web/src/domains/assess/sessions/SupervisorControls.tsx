"use client";

import { useState } from "react";
import { ActionMenu, Alert, Button } from "@/foundation/ui";
import { assessMeta } from "@/foundation/ui/b2bTokens";
import { overrides, runControls, setAutoAdvance } from "@/domains/assess/sessions/api";
import type { CircuitConsole, ConsoleSlot } from "@/domains/assess/sessions/api";
import { HIRE_CONSOLE, HIRE_JUMP_DIALOG, hireAutoAdvance, hireRedoDialog, jumpChoices } from "@/domains/assess/sessions/hireConsole";
import { orderedSlots, stationLabel } from "@/domains/assess/sessions/support";
import { primaryTurnAction } from "@/domains/assess/sessions/turns";
import { OverrideDialog, type OverrideInput, type OverrideRequest } from "@/domains/assess/sessions/OverrideDialog";
import type { AssessWords } from "@/capabilities/assess-words/vocabulary";
import { useAssessWords } from "@/capabilities/assess-words";

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

  // Redo acts on the station running now; Jump offers every other one.
  const activeSlot = orderedSlots(data).find((slot) => slot.id === circuit.active_slot_id);
  const otherSlots = jumpChoices(data);
  const redoJump = [
    {
      label: HIRE_CONSOLE.redo,
      disabled: working || !activeSlot,
      hint: waitHint ?? (activeSlot ? undefined : HIRE_CONSOLE.noStationRunning),
      onSelect: () => activeSlot && openRequest(redoRequest(orgSlug, circuitId, activeSlot)),
    },
    {
      label: HIRE_CONSOLE.jump,
      disabled: working || otherSlots.length === 0,
      hint: waitHint ?? (otherSlots.length === 0 ? HIRE_CONSOLE.noOtherStation : undefined),
      onSelect: () => openRequest(jumpRequest(orgSlug, circuitId, otherSlots)),
    },
  ];

  async function copyObserverLink() {
    try {
      await navigator.clipboard.writeText(window.location.href);
    } catch {
      // Clipboard refused: the address bar still holds the link.
    }
  }

  // Anyone who has not sat can be marked absent, before or during the run.
  const slots = data.slots ?? [];
  const hasSat = new Set(
    slots.filter((slot) => slot.status !== "scheduled" && slot.status !== "reading").map((slot) => slot.trainee.user_id),
  );
  const absentItems = [...new Map(slots.map((slot) => [slot.trainee.user_id, slot])).values()]
    .filter((slot) => !hasSat.has(slot.trainee.user_id))
    .map((slot) => ({
      label: `Mark ${slot.trainee.name ?? w.trainee} absent`,
      disabled: working,
      hint: waitHint,
      onSelect: () => openRequest(absentRequest(orgSlug, circuitId, slot.trainee.user_id, slot.trainee.name ?? w.trainee, w)),
    }));

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
          Pausing, adding time or skipping asks for a reason. {`It is saved with the ${w.circuit}.`}
        </p>
      )}

      <div className="flex flex-wrap items-center gap-2.5">
        {!started ? (
          <>
          <Button
            themeType="b2b"
            variant="commit"
            isLoading={busy === "start"}
            disabled={working}
            onClick={() => run("start", () => runControls.start(orgSlug, circuitId))}
          >
            {hire ? HIRE_CONSOLE.start : `Start ${w.circuit}`}
          </Button>
          <ActionMenu label={`More ${w.circuit} controls`} items={absentItems} />
          </>
        ) : (
          <>
            <Button
              themeType="b2b"
              variant="commit"
              isLoading={busy === "advance"}
              disabled={working}
              onClick={() =>
                training && turn.kind === "end"
                  ? openRequest(endRequest(orgSlug, circuitId, w, hire))
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
              label={hire ? HIRE_CONSOLE.menu : `More ${w.circuit} controls`}
              items={[
                { label: hire ? HIRE_CONSOLE.addTime : "Add time", disabled: working, hint: waitHint, onSelect: () => openRequest(extendRequest(orgSlug, circuitId, hire)) },
                { label: hire ? HIRE_CONSOLE.restartClock : "Restart the timer", disabled: working, hint: waitHint, onSelect: () => openRequest(resetRequest(orgSlug, circuitId)) },
                { label: "Resend the patient", disabled: working, hint: waitHint, onSelect: () => openRequest(resendRequest(orgSlug, circuitId)) },
                { label: "Allow one re-join", disabled: working, hint: waitHint, onSelect: () => openRequest(rejoinRequest(orgSlug, circuitId, w)) },
                ...(hire ? redoJump : []),
                ...absentItems,
                ...(hire ? [{ label: HIRE_CONSOLE.observerLink, onSelect: () => void copyObserverLink() }] : []),
                ...(training && turn.kind === "end"
                  ? []
                  : [{ label: hire ? HIRE_CONSOLE.end : `End ${w.circuit}`, tone: "danger" as const, disabled: working, hint: waitHint, onSelect: () => openRequest(endRequest(orgSlug, circuitId, w, hire)) }]),
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
          {hire ? hireAutoAdvance(circuit.auto_advance) : <>Move on by itself when time is up. If off, you press {training ? `the button above to bring in the next ${w.trainee}` : "Next station"}.</>}
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

function endRequest(slug: string, circuitId: string, w: AssessWords, hire: boolean): OverrideRequest {
  return {
    name: "end",
    title: hire ? HIRE_CONSOLE.endTitle : `End the ${w.circuit}`,
    lead: "Any station nobody has taken is marked as skipped. You cannot undo this. End it only when everyone has finished.",
    commitLabel: hire ? HIRE_CONSOLE.endTitle : `End the ${w.circuit}`,
    tone: "danger",
    run: ({ reason }) => runControls.end(slug, circuitId, reason),
  };
}

function rejoinRequest(slug: string, circuitId: string, w: AssessWords): OverrideRequest {
  return {
    name: "rejoin",
    title: "Allow one re-join",
    lead: `Lets the ${w.trainee} whose connection dropped back into this station, once. The clock does not stop or restart; use Add time if they need it.`,
    commitLabel: "Allow re-join",
    reasonRequired: true,
    run: ({ reason }) => overrides.allowRejoin(slug, circuitId, reason ?? ""),
  };
}

function absentRequest(slug: string, circuitId: string, traineeId: string, name: string, w: AssessWords): OverrideRequest {
  return {
    name: "absent",
    title: `Mark ${name} absent`,
    lead: `${name} has not joined. Their stations are skipped and they cannot join this ${w.circuit} afterwards.`,
    commitLabel: "Mark absent",
    tone: "danger",
    reasonRequired: true,
    run: ({ reason }) => overrides.markAbsent(slug, circuitId, traineeId, reason ?? ""),
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
