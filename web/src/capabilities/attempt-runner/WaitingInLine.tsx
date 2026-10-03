"use client";

import { Button, Spinner } from "@/foundation/ui";

/**
 * What a candidate sees while every patient is busy.
 *
 * Without it the candidate past the last seat joined an empty room and waited
 * for a patient who never came, with nothing to say why.
 */
export function WaitingInLine({ position, onLeave }: { position: number | null; onLeave: () => Promise<void> }) {
  return (
    <div className="flex flex-col items-start gap-3 py-6" role="status" aria-live="polite">
      <span className="flex h-10 w-10 items-center justify-center rounded-control bg-b2c-surface-muted">
        <Spinner />
      </span>
      <h2 className="text-osce-subheading font-semibold text-osce-ink-900">All our patients are busy</h2>
      <p className="max-w-sm text-osce-body text-b2c-text-muted">
        {position ? `You are number ${position} in line. ` : ""}
        Keep this page open to hold your place. Your time starts when the patient joins.
      </p>
      <Button variant="secondary" onClick={() => void onLeave()}>
        Leave the line
      </Button>
    </div>
  );
}
