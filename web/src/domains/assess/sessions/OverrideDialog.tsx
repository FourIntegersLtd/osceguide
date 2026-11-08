"use client";

import { useState } from "react";
import { assessFormHeading, assessFormStack, assessHelper } from "@/foundation/ui/b2bTokens";
import { PeopleDialog } from "@/domains/assess/ui";
import {
  MAX_EXTEND_SECONDS,
  validOverrideSeconds,
} from "@/domains/assess/sessions/support";
import { boardInput } from "@/foundation/ui/boardKit";
import { Select } from "@/foundation/ui";

export type OverrideInput = { reason: string | null; seconds: number; choice: string };

export interface OverrideRequest {
  /** The control being confirmed, used as the busy key. */
  name: string;
  title: string;
  lead: string;
  commitLabel: string;
  tone?: "commit" | "danger";
  /** Shown when the override needs a number as well as a reason. */
  seconds?: number;
  /** Shown when the override picks one of several stations (Jump to…). The first is preselected. */
  choices?: { value: string; label: string }[];
  choiceLabel?: string;
  run: (input: OverrideInput) => Promise<unknown>;
}

/**
 * A human stepping into an examination, and saying why.
 *
 * Every override the backend accepts carries an optional `reason`, written to
 * the interventions record beside the action. Optional there, asked for here:
 * an examination that cannot say why its clock was extended is not one anybody
 * can defend afterwards. The reason is not *required* — a fire alarm is a poor
 * moment to insist on a form — so the commit stays enabled either way.
 */
export function OverrideDialog({
  request,
  busy,
  error,
  onClose,
  onCommit,
}: {
  request: OverrideRequest | null;
  busy: boolean;
  error: string | null;
  onClose: () => void;
  onCommit: (input: OverrideInput) => void;
}) {
  // The form is mounted by the request and unmounted with it, so each override
  // starts blank. Carrying the last one's reason into the next would write it
  // to the record as though it were this one's.
  if (!request) return null;
  return (
    <OverrideForm
      request={request}
      busy={busy}
      error={error}
      onClose={onClose}
      onCommit={onCommit}
    />
  );
}

function OverrideForm({
  request,
  busy,
  error,
  onClose,
  onCommit,
}: {
  request: OverrideRequest;
  busy: boolean;
  error: string | null;
  onClose: () => void;
  onCommit: (input: OverrideInput) => void;
}) {
  const [reason, setReason] = useState("");
  const [seconds, setSeconds] = useState(request.seconds ?? 60);
  const [choice, setChoice] = useState(request.choices?.[0]?.value ?? "");

  return (
    <PeopleDialog
      open
      title={request.title}
      lead={request.lead}
      error={error}
      busy={busy}
      commitDisabled={request.seconds !== undefined && !validOverrideSeconds(seconds)}
      tone={request.tone ?? "commit"}
      commitLabel={request.commitLabel}
      busyLabel="Working…"
      onClose={onClose}
      onCommit={() => onCommit({ reason: reason.trim() || null, seconds, choice })}
    >
      <div className={assessFormStack}>
        {request.choices ? (
          <label className={assessFormHeading}>
            <span className="text-assess-label font-medium">{request.choiceLabel}</span>
            <Select value={choice} onChange={(event) => setChoice(event.target.value)}>
              {request.choices.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </label>
        ) : null}

        {request.seconds !== undefined ? (
          <label className={assessFormHeading}>
            <span className="text-assess-label font-medium">Seconds to add</span>
            <input
              type="number"
              min={1}
              max={MAX_EXTEND_SECONDS}
              value={seconds}
              onChange={(event) => setSeconds(Number(event.target.value))}
              className={boardInput}
            />
          </label>
        ) : null}

        <label className={assessFormHeading}>
          <span className="text-assess-label font-medium">
            Reason <span className="font-normal text-osce-ink-500">(kept with the record)</span>
          </span>
          <input
            value={reason}
            maxLength={500}
            placeholder="The fire alarm went off"
            onChange={(event) => setReason(event.target.value)}
            className={boardInput}
          />
          <span className={assessHelper}>Optional. Your answer is saved with the circuit.</span>
        </label>
      </div>
    </PeopleDialog>
  );
}
