"use client";

import { useAssessWords } from "@/capabilities/assess-words";
import { examConfirmMessage } from "@/capabilities/authoring/lib/authoringCopy";
import { AuthoringConfirm } from "@/capabilities/authoring/parts/AuthoringConfirm";
import { deleteExam, retireExam, type Exam } from "@/capabilities/authoring/api";
import type { AuthoringScope } from "@/capabilities/authoring/api/scope";
import type { ActionState } from "@/capabilities/authoring/parts/useAction";

const KINDS = {
  retire: {
    confirmText: "Retire exam",
    write: retireExam,
  },
  delete: {
    confirmText: "Delete exam",
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
  const w = useAssessWords();
  const { confirmText, write } = KINDS[kind];
  const key = exam ? `${kind}:${exam.id}` : null;
  const confirm = () => {
    if (!exam || !key) return;
    void action.run(key, () => write(scope, exam.id)).then((ok) => {
      if (ok) {
        onCancel();
        onDone?.();
      }
    });
  };
  const heading = exam ? `${kind === "retire" ? "Retire" : "Delete"} "${exam.name}"?` : "Confirm";
  return (
    <AuthoringConfirm
      isOpen={exam !== null}
      onCancel={onCancel}
      onConfirm={confirm}
      isLoading={key !== null && action.busy === key}
      tone="danger"
      title={heading}
      confirmText={confirmText}
      error={action.error}
      message={examConfirmMessage(kind, w)}
    />
  );
}
