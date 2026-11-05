"use client";

import { useState } from "react";
import { ConfirmModal } from "@/foundation/ui";
import { assessErrorMessage } from "@/domains/assess/errorCopy";
import { hasCode } from "@/foundation/platform-client";
import { cancelSitting, deleteCircuit, type Circuit } from "@/domains/assess/api";

/** The write a sitting's admin has asked for and not yet confirmed. */
export type PendingSittingAction = { kind: "cancel" } | { kind: "delete"; circuit: Circuit } | null;

/** Confirms cancelling a sitting or deleting a never-started circuit (R-7), and says why the server refused. */
export function SittingActionDialog({
  orgSlug,
  sittingId,
  pending,
  onClose,
  onDone,
}: {
  orgSlug: string;
  sittingId: string;
  pending: PendingSittingAction;
  onClose: () => void;
  onDone: () => void;
}) {
  const [refused, setRefused] = useState<string | null>(null);

  const close = () => {
    setRefused(null);
    onClose();
  };
  const run = async (action: () => Promise<unknown>) => {
    try {
      await action();
      close();
      onDone();
    } catch (cause) {
      setRefused(refusal(cause));
    }
  };

  if (pending?.kind === "delete") {
    const { circuit } = pending;
    return (
      <ConfirmModal
        isOpen
        title={`Delete ${circuit.name}?`}
        message="Its candidates and stations come off this sitting. Nothing has been sat on it yet."
        confirmText="Delete circuit"
        tone="danger"
        error={refused}
        onCancel={close}
        onConfirm={() => run(() => deleteCircuit(orgSlug, circuit.id))}
      />
    );
  }
  return (
    <ConfirmModal
      isOpen={pending?.kind === "cancel"}
      title="Cancel this sitting?"
      message="Nobody can take it once it is cancelled. Nothing has started, so no attempt is lost."
      confirmText="Cancel sitting"
      cancelText="Cancel"
      tone="danger"
      error={refused}
      onCancel={close}
      onConfirm={() => run(() => cancelSitting(orgSlug, sittingId))}
    />
  );
}

/** A cancel or delete refusal, by its code: something started since the page loaded. */
function refusal(cause: unknown): string {
  if (hasCode(cause, "sitting_locked")) {
    return "A circuit on this sitting has started, so it cannot be cancelled. End its circuits instead.";
  }
  if (hasCode(cause, "circuit_locked")) {
    return "This circuit has started, so it holds what was sat and cannot be deleted.";
  }
  return assessErrorMessage(cause);
}
