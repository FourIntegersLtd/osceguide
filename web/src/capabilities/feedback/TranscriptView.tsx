"use client";

import { LuStethoscope } from "react-icons/lu";
import { HiUser } from "react-icons/hi";
import { HiOutlineDocumentText } from "react-icons/hi2";
import { B2CEmptyState } from "@/foundation/ui";
import type { Transcript } from "@/capabilities/feedback/api";

/**
 * What was said, in order. The same view for a candidate and a marker.
 *
 * The doctor's turn sits on the left with the stethoscope and the patient's on
 * the right, which is the retiring screen's arrangement: a candidate reading
 * their own consultation back recognises their own side of it at a glance.
 */
export function TranscriptView({ transcript }: { transcript: Transcript }) {
  if (transcript.messages.length === 0) {
    return (
      <B2CEmptyState
        icon={HiOutlineDocumentText}
        title="Nothing was transcribed"
        description="No speech was recorded for this consultation."
      />
    );
  }

  // One card of plain rows (canvas `train-transcript`): who spoke, then what
  // they said. The candidate's lines carry the accent tile so a scan down the
  // left edge shows the turns.
  return (
    <div className="space-y-3">
      <ol className="divide-y divide-osce-border-light rounded-osce-lg border border-osce-border bg-osce-surface">
        {transcript.messages.map((message) => {
          const isCandidate = message.role === "user" || message.role === "candidate";
          return (
            <li key={message.seq} className="flex gap-3 px-5 py-3.5">
              <span
                className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-control ${
                  isCandidate
                    ? "bg-osce-accent-subtle text-osce-accent"
                    : "bg-b2c-surface-muted text-b2c-text-secondary"
                }`}
              >
                {isCandidate ? (
                  <LuStethoscope className="h-3.5 w-3.5" aria-label="You" />
                ) : (
                  <HiUser className="h-3.5 w-3.5" aria-label="The other speaker" />
                )}
              </span>
              <p className="min-w-0 whitespace-pre-wrap text-osce-body leading-relaxed text-osce-ink-900">
                {message.message}
              </p>
            </li>
          );
        })}
      </ol>
      {!transcript.complete && (
        <p className="text-osce-meta text-b2c-text-muted">
          This transcript is still being delivered.
        </p>
      )}
    </div>
  );
}
