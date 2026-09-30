"use client";

import { useState } from "react";
import { Input } from "@/foundation/ui";
import { Dialog } from "@/domains/assess/team/chrome";

export interface OverrideRequest {
  /** The control being confirmed, used as the busy key. */
  name: string;
  title: string;
  lead: string;
  commitLabel: string;
  tone?: "commit" | "danger";
  /** Shown when the override needs a number as well as a reason. */
  seconds?: number;
  run: (input: { reason: string | null; seconds: number }) => Promise<unknown>;
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
  onCommit: (input: { reason: string | null; seconds: number }) => void;
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
  onCommit: (input: { reason: string | null; seconds: number }) => void;
}) {
  const [reason, setReason] = useState("");
  const [seconds, setSeconds] = useState(request.seconds ?? 60);

  return (
    <Dialog
      open
      title={request.title}
      lead={request.lead}
      error={error}
      busy={busy}
      tone={request.tone ?? "commit"}
      commitLabel={request.commitLabel}
      busyLabel="Working…"
      onClose={onClose}
      onCommit={() => onCommit({ reason: reason.trim() || null, seconds })}
    >
      {request.seconds !== undefined ? (
        <label className="block">
          <span className="text-osce-caption font-medium text-b2b-headline">Seconds to add</span>
          <Input
            type="number"
            min={1}
            max={3600}
            value={seconds}
            onChange={(event) => setSeconds(Number(event.target.value))}
            className="mt-1"
          />
        </label>
      ) : null}

      <label className="block">
        <span className="text-osce-caption font-medium text-b2b-headline">
          Reason <span className="font-normal text-b2b-mid">(kept with the record)</span>
        </span>
        <Input
          value={reason}
          maxLength={500}
          placeholder="The fire alarm went off"
          onChange={(event) => setReason(event.target.value)}
          className="mt-1"
        />
      </label>
    </Dialog>
  );
}
