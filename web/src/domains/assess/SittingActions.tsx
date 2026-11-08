"use client";

import { useState } from "react";
import { ConfirmModal } from "@/foundation/ui";
import type { AssessWords } from "@/capabilities/assess-words";
import { assessErrorMessage } from "@/domains/assess/errorCopy";
import { hasCode } from "@/foundation/platform-client";
import { cancelSitting, deleteCircuit, type Circuit } from "@/domains/assess/api";
import { useAssessWords } from "@/capabilities/assess-words";
import { cancelMessage } from "@/domains/assess/sittingCopy";

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
  const w = useAssessWords();
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
      setRefused(refusal(cause, w));
    }
  };

  if (pending?.kind === "delete") {
    const { circuit } = pending;
    return (
      <ConfirmModal
        isOpen
        title={`Delete ${circuit.name}?`}
        message={`Its candidates and stations come off this ${w.sitting}. Nothing has been sat on it yet.`}
        confirmText={`Delete ${w.circuit}`}
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
      title={`Cancel this ${w.sitting}?`}
      message={cancelMessage(w)}
      confirmText={`Cancel ${w.sitting}`}
      cancelText="Cancel"
      tone="danger"
      error={refused}
      onCancel={close}
      onConfirm={() => run(() => cancelSitting(orgSlug, sittingId))}
    />
  );
}

/** A cancel or delete refusal, by its code: something started since the page loaded. */
function refusal(cause: unknown, w: AssessWords): string {
  if (hasCode(cause, "sitting_locked")) {
    return `A ${w.circuit} on this ${w.sitting} has started, so it cannot be cancelled. End its ${w.circuits} instead.`;
  }
  if (hasCode(cause, "circuit_locked")) {
    return w.hiring
      ? `This ${w.circuit} has started and holds candidates' work, so it cannot be deleted. You can end it instead.`
      : "This circuit has started, so it holds what was sat and cannot be deleted.";
  }
  return assessErrorMessage(cause, w);
}
