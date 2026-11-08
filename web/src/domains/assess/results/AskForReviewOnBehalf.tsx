"use client";

import { useState } from "react";
import { errorMessage } from "@/foundation/hooks";
import { PeopleDialog as Dialog, Note } from "@/domains/assess/ui";
import { requestReviewForCandidate } from "@/domains/assess/results/api";
import { useAssessWords } from "@/capabilities/assess-words";
import { boardButtonSmall, boardInput, boardLabel } from "@/foundation/ui/boardKit";

/** Staff record a review request for a candidate who asked in person or by email. */
export function AskForReviewOnBehalf({
  orgSlug,
  sittingId,
  traineeId,
}: {
  orgSlug: string;
  sittingId: string;
  traineeId: string;
}) {
  const w = useAssessWords();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function commit() {
    setBusy(true);
    setError(null);
    try {
      await requestReviewForCandidate(orgSlug, sittingId, traineeId, reason.trim());
      setDone(true);
      setOpen(false);
      setReason("");
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {done ? <Note tone="ok" role="status">Review request recorded. It is in the appeals queue under Results.</Note> : null}
      <button type="button" className={boardButtonSmall} onClick={() => setOpen(true)}>
        Record a review request
      </button>
      <Dialog
        open={open}
        title="Record a review request"
        lead={`Use this when the ${w.trainee} asked outside the product. Their reason goes to the second marker.`}
        error={error}
        busy={busy}
        commitDisabled={reason.trim() === ""}
        commitLabel="Record request"
        busyLabel="Saving…"
        onClose={() => setOpen(false)}
        onCommit={() => void commit()}
      >
        <div>
          <label htmlFor="behalf-reason" className={boardLabel}>Reason</label>
          <textarea id="behalf-reason" className={boardInput} rows={4} maxLength={4000} value={reason} onChange={(e) => setReason(e.target.value)} />
        </div>
      </Dialog>
    </>
  );
}
