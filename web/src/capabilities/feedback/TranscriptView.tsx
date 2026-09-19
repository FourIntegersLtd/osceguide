"use client";

import { Card, cn } from "@/foundation/ui";
import type { Transcript } from "@/capabilities/attempt-runner";

/** What was said, in order. The same view for a candidate and a marker. */
export function TranscriptView({ transcript }: { transcript: Transcript }) {
  if (transcript.messages.length === 0) {
    return (
      <Card>
        <p className="text-sm text-ink-muted">Nothing was transcribed for this attempt.</p>
      </Card>
    );
  }

  return (
    <Card title="Transcript" description={transcript.complete ? undefined : "Still being delivered."}>
      <ol className="flex flex-col gap-3">
        {transcript.messages.map((message) => {
          const isCandidate = message.role === "user" || message.role === "candidate";
          return (
            <li
              key={message.seq}
              className={cn("flex flex-col gap-0.5", isCandidate ? "items-end" : "items-start")}
            >
              <span className="text-xs uppercase tracking-wide text-ink-subtle">
                {isCandidate ? "You" : "Patient"}
              </span>
              <p
                className={cn(
                  "max-w-[85%] rounded-panel px-3 py-2 text-sm",
                  isCandidate ? "bg-accent-subtle text-ink" : "bg-surface-raised text-ink-muted",
                )}
              >
                {message.message}
              </p>
            </li>
          );
        })}
      </ol>
    </Card>
  );
}
