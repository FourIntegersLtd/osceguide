"use client";

import { ConfirmModal } from "@/foundation/ui";
import { deleteExam, retireExam, type Exam } from "@/capabilities/authoring/api";
import type { AuthoringScope } from "@/capabilities/authoring/api/scope";
import type { ActionState } from "@/capabilities/authoring/parts/useAction";

const KINDS = {
  retire: {
    confirmText: "Retire exam",
    message:
      "It stops being offered for new practice and sittings, and cannot be published again. What was already attempted against it stays as it is.",
    write: retireExam,
  },
  delete: {
    confirmText: "Delete exam",
    message:
      "Only a draft nothing was ever built on can be deleted this way. Anything with a station, a sitting or an attempt against it cannot be deleted. Retire it instead.",
    write: deleteExam,
  },
} as const;

/** "Retire exam?" and "Delete exam?": shared by the Exams list and an exam's own page. */
export function ExamConfirm({
  kind,
  scope,
  exam,
  action,
  onCancel,
  onDone,
}: {
  kind: keyof typeof KINDS;
  scope: AuthoringScope;
  exam: Exam | null;
  action: ActionState;
  onCancel: () => void;
  /** Runs once the write took, after the modal's own state is cleared. */
  onDone?: () => void;
}) {
  const { confirmText, message, write } = KINDS[kind];
  const key = exam ? `${kind}:${exam.id}` : null;
  return (
    <ConfirmModal
      isOpen={exam !== null}
      onCancel={onCancel}
      onConfirm={() => {
        if (!exam || !key) return;
        void action.run(key, () => write(scope, exam.id)).then((ok) => {
          if (ok) {
            onCancel();
            onDone?.();
          }
        });
      }}
      isLoading={key !== null && action.busy === key}
      tone="danger"
      title={exam ? `${kind === "retire" ? "Retire" : "Delete"} "${exam.name}"?` : "Confirm"}
      confirmText={confirmText}
      error={action.error}
      message={message}
    />
  );
}
