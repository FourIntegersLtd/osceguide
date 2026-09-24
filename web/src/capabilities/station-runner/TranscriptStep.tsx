"use client";

import { useState } from "react";
import { HiOutlineArrowDownTray, HiOutlineClock } from "react-icons/hi2";
import { Alert, AsyncBoundary, Button, Modal } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { TranscriptView } from "@/capabilities/feedback";
import { listMyAttempts, readTranscript } from "@/capabilities/attempt-runner";
import { downloadTranscript } from "@/capabilities/attempt-runner/transcriptDocument";

/**
 * What was said, in the panel that held the brief during the consultation.
 *
 * This is where the transcript lives in the product — the right-hand column of
 * the consultation screen once it is over — rather than being a section of its
 * own in the navigation, which is what it had become.
 *
 * "Load Previous" opens the other times this station has been sat. The old
 * screen sent people to a `/transcripts` page with a query string; the list is
 * short and belongs here.
 */
export function TranscriptStep({
  attemptId,
  stationVersionId,
}: {
  attemptId: string | null;
  stationVersionId: string | null;
}) {
  const [showing, setShowing] = useState(attemptId);
  const [picking, setPicking] = useState(false);

  const current = showing ?? attemptId;
  const transcript = useAsync(
    (signal) => (current ? readTranscript(current, signal) : Promise.resolve(null)),
    [current],
  );

  if (!current) {
    return (
      <div className="p-4 sm:p-5">
        <Alert tone="info">There is no consultation recorded for this station yet.</Alert>
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-5">
        <AsyncBoundary state={transcript}>
          {(data) =>
            data && data.messages.length > 0 ? (
              <TranscriptView transcript={data} />
            ) : (
              <Alert tone="info">Nothing was recorded for this consultation.</Alert>
            )
          }
        </AsyncBoundary>
      </div>

      <div className="flex flex-wrap items-center justify-end gap-2 border-t border-b2c-border p-3">
        {stationVersionId && (
          <Button type="button" variant="ghost" size="sm" onClick={() => setPicking(true)}>
            <HiOutlineClock className="h-4 w-4" aria-hidden /> Load Previous
          </Button>
        )}
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => transcript.data && downloadTranscript(transcript.data)}
          disabled={!transcript.data?.messages.length}
        >
          <HiOutlineArrowDownTray className="h-4 w-4" aria-hidden /> Download Transcript
        </Button>
      </div>

      {picking && stationVersionId && (
        <PreviousAttempts
          stationVersionId={stationVersionId}
          onPick={(id) => {
            setShowing(id);
            setPicking(false);
          }}
          onClose={() => setPicking(false)}
        />
      )}
    </div>
  );
}

/** Every time this station has been sat, newest first. */
function PreviousAttempts({
  stationVersionId,
  onPick,
  onClose,
}: {
  stationVersionId: string;
  onPick: (attemptId: string) => void;
  onClose: () => void;
}) {
  const state = useAsync(
    (signal) => listMyAttempts({ stationVersionId, limit: 25 }, signal),
    [stationVersionId],
  );

  return (
    <Modal onClose={onClose} width="min(95vw, 32rem)" height="fit-content">
      <div className="space-y-3 p-5">
        <h2 className="text-osce-h3 font-semibold text-osce-ink-900">Previous consultations</h2>
        <AsyncBoundary state={state}>
          {(page) =>
            page.items.length === 0 ? (
              <Alert tone="info">You have not sat this station before.</Alert>
            ) : (
              <ul className="divide-y divide-b2c-border">
                {page.items.map((item) => (
                  <li key={item.id}>
                    <button
                      type="button"
                      onClick={() => onPick(item.id)}
                      className="flex w-full items-center justify-between gap-3 py-3 text-left"
                    >
                      <span className="text-osce-body text-osce-ink-900">
                        {new Date(item.created_at).toLocaleString("en-GB", {
                          day: "numeric",
                          month: "long",
                          year: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                      <span className="text-osce-meta text-b2c-text-muted">
                        {item.has_result ? "Marked" : "Not marked"}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )
          }
        </AsyncBoundary>
      </div>
    </Modal>
  );
}
