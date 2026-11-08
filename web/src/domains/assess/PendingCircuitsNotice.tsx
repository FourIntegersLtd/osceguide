"use client";

import { useState } from "react";
import { Alert, Button, Spinner } from "@/foundation/ui";
import { assessErrorMessage } from "@/domains/assess/errorCopy";
import {
  circuitsMade,
  clearPending,
  createSittingCircuits,
  loadPending,
  savePending,
} from "@/domains/assess/scheduleCircuits";
import { useAssessWords } from "@/capabilities/assess-words";

/**
 * Shown on a sitting the wizard made but could not finish building.
 *
 * "Try again" posts the circuits from the answers the wizard had, carrying on
 * after any that were made, so a retry neither duplicates nor skips a candidate.
 */
export function PendingCircuitsNotice({
  orgSlug,
  sittingId,
  onDone,
}: {
  orgSlug: string;
  sittingId: string;
  onDone: () => void;
}) {
  const w = useAssessWords();
  const [pending, setPending] = useState(() => loadPending(sittingId));
  const [busy, setBusy] = useState(false);
  if (!pending) return null;

  const retry = async () => {
    setBusy(true);
    try {
      await createSittingCircuits(orgSlug, sittingId, pending.draft, pending.created);
      clearPending(sittingId);
      setPending(null);
      onDone();
    } catch (cause) {
      const next = { ...pending, created: circuitsMade(cause, pending.created), message: assessErrorMessage(cause, w) };
      savePending(sittingId, next);
      setPending(next);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Alert tone="danger" title="The circuits were not made">
      <p>{pending.message}</p>
      <div className="mt-2">
        <Button themeType="b2b" variant="secondary" disabled={busy} onClick={() => void retry()}>
          {busy ? <Spinner label="Making the circuits" className="text-current" /> : "Try again"}
        </Button>
      </div>
    </Alert>
  );
}
