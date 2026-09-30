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

  return (
    <div className="space-y-6">
      {transcript.messages.map((message) => {
        const isCandidate = message.role === "user" || message.role === "candidate";
        return (
          <div
            key={message.seq}
            className={`flex gap-4 ${isCandidate ? "flex-row" : "flex-row-reverse"}`}
          >
            <div
              className={`flex items-center justify-center w-10 h-10 rounded-full shrink-0 ${
                isCandidate
                  ? "bg-osce-accent-subtle text-osce-accent"
                  : "bg-osce-border-light text-osce-ink-600"
              }`}
            >
              {isCandidate ? (
                <LuStethoscope className="w-5 h-5" />
              ) : (
                <HiUser className="w-5 h-5" />
              )}
            </div>
            <div
              className={`max-w-[85%] sm:max-w-[75%] rounded-2xl px-5 py-3 ${
                isCandidate
                  ? "bg-osce-accent-subtle text-osce-accent-hover"
                  : "bg-osce-border-light text-osce-ink-900"
              }`}
            >
              <p className="text-osce-body leading-relaxed whitespace-pre-wrap">
                {message.message}
              </p>
            </div>
          </div>
        );
      })}
      {!transcript.complete && (
        <p className="text-osce-meta text-b2c-text-muted">
          This transcript is still being delivered.
        </p>
      )}
    </div>
  );
}
