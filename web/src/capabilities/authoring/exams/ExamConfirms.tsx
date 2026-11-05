"use client";

import { ConfirmModal } from "@/foundation/ui";
import { deleteExam, retireExam, type Exam } from "@/capabilities/authoring/api";
import type { AuthoringScope } from "@/capabilities/authoring/api/scope";
import type { ActionState } from "@/capabilities/authoring/parts/useAction";

type Props = {
  scope: AuthoringScope;
  exam: Exam | null;
  action: ActionState;
  onCancel: () => void;
  /** Runs once the write took, after the modal's own state is cleared. */
  onDone?: () => void;
};

/** "Retire exam?": shared by the Exams list and an exam's own page. */
export function RetireExamConfirm({ scope, exam, action, onCancel, onDone }: Props) {
  return (
    <ConfirmModal
      isOpen={exam !== null}
      onCancel={onCancel}
      onConfirm={() => {
        if (!exam) return;
        void action.run(`retire:${exam.id}`, () => retireExam(scope, exam.id)).then((ok) => {
          if (ok) {
            onCancel();
            onDone?.();
          }
        });
      }}
      isLoading={exam !== null && action.busy === `retire:${exam.id}`}
      tone="danger"
      title={exam ? `Retire "${exam.name}"?` : "Confirm"}
      confirmText="Retire exam"
      error={action.error}
      message="It stops being offered for new practice and sittings, and cannot be published again. What was already attempted against it stays as it is."
    />
  );
}

/** "Delete exam?": shared by the Exams list and an exam's own page. */
export function DeleteExamConfirm({ scope, exam, action, onCancel, onDone }: Props) {
  return (
    <ConfirmModal
      isOpen={exam !== null}
      onCancel={onCancel}
      onConfirm={() => {
        if (!exam) return;
        void action.run(`delete:${exam.id}`, () => deleteExam(scope, exam.id)).then((ok) => {
          if (ok) {
            onCancel();
            onDone?.();
          }
        });
      }}
      isLoading={exam !== null && action.busy === `delete:${exam.id}`}
      tone="danger"
      title={exam ? `Delete "${exam.name}"?` : "Confirm"}
      confirmText="Delete exam"
      error={action.error}
      message="Only a draft nothing was ever built on can be deleted this way. Anything with a station, a sitting or an attempt against it cannot be deleted. Retire it instead."
    />
  );
}
