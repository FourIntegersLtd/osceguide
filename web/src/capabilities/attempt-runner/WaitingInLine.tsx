"use client";

import { Button, Spinner } from "@/foundation/ui";

/**
 * What a candidate sees while every patient is busy.
 *
 * Without it the candidate past the last seat joined an empty room and waited
 * for a patient who never came, with nothing to say why.
 */
export function WaitingInLine({ position, onLeave }: { position: number | null; onLeave: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-8 text-center" role="status" aria-live="polite">
      <Spinner />
      <p className="text-osce-body font-medium text-b2c-text">All our patients are busy</p>
      <p className="max-w-xs text-osce-meta text-b2c-text-muted">
        {position ? `You are number ${position} in line. ` : ""}
        We will connect you as soon as a patient is free. Keep this page open to hold your place.
        Your consultation time starts when the patient joins, not before.
      </p>
      <Button variant="ghost" size="sm" onClick={onLeave}>
        Leave the line
      </Button>
    </div>
  );
}
