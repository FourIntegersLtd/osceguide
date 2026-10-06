"use client";

import { useState } from "react";
import {
  HiOutlineArrowUpTray,
  HiOutlineNoSymbol,
  HiOutlinePencilSquare,
  HiOutlinePlusCircle,
  HiOutlineTrash,
} from "react-icons/hi2";
import { Alert, Checkbox, ConfirmModal, StepGuide } from "@/foundation/ui";
import { AuthoringButton } from "@/capabilities/authoring/parts/AuthoringButton";
import {
  AuthoringIconAction,
  AuthoringRowActions,
} from "@/capabilities/authoring/parts/AuthoringIconAction";
import { AuthoringListRow } from "@/capabilities/authoring/parts/AuthoringListRow";
import { useAsync } from "@/foundation/hooks";
import {
  createExam,
  deleteExam,
  listExams,
  publishExam,
  retireExam,
  updateExam,
  type Exam,
} from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { useAction } from "@/capabilities/authoring/parts/useAction";
import { ListCard } from "@/capabilities/authoring/parts/ListCard";
import { StatusBadge } from "@/capabilities/authoring/parts/StatusPills";
import { AuthoringDialog } from "@/capabilities/authoring/parts/AuthoringDialog";
import { examNextAction, examSteps } from "@/capabilities/authoring/sections/examSteps";
import { ExamFields, blankExam, type ExamDraft } from "@/capabilities/authoring/sections/ExamFields";

/**
 * Exams: what an organisation assesses against.
 *
 * An institution writes its own without asking the platform and without
 * picking from a list — its `finals` and another school's are different rows —
 * and the same screen, under the staff scope, writes the platform catalogue.
 * The list shows every status (a new exam stays visible, with a Draft pill);
 * "Drafts only" narrows it to the drafts.
 */
export function ExamsSection() {
  const scope = useAuthoringScope();
  const [draftsOnly, setDraftsOnly] = useState(false);
  const exams = useAsync(
    (signal) => listExams(scope, { status: draftsOnly ? "draft" : "all" }, signal),
    [scope.base, draftsOnly],
  );
  const action = useAction(exams.reload);

  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<ExamDraft>(blankExam);
  const [editing, setEditing] = useState<Exam | null>(null);
  const [deleting, setDeleting] = useState<Exam | null>(null);
  const [retiring, setRetiring] = useState<Exam | null>(null);

  const items = exams.data?.items ?? [];

  // The form's scheme, not the stored one, so the rail follows the pick.
  const editingExam = editing ? { status: editing.status, rubric_version_id: form.rubricVersionId } : null;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Checkbox
          checked={draftsOnly}
          onChange={(e) => setDraftsOnly(e.target.checked)}
          label="Drafts only"
          className="items-center"
        />
        <AuthoringButton
          variant="commit"
          size="sm"
          className="gap-2"
          onClick={() => {
            setForm(blankExam);
            setCreating(true);
          }}
        >
          <HiOutlinePlusCircle className="h-4 w-4 shrink-0" aria-hidden />
          Create exam
        </AuthoringButton>
      </div>

      {action.error ? <Alert tone="danger">{action.error}</Alert> : null}

      <ListCard
        count={items.length}
        countLabel="Exams"
        loading={exams.loading && !exams.data}
        error={exams.error ? exams.error.message : null}
        onDismissError={exams.reload}
        empty={{
          title: draftsOnly ? "No draft exams" : "No exams yet",
          description: draftsOnly
            ? "Everything here is published. Clear the filter to see the whole catalogue."
            : "Create an exam, attach a marking scheme version, then publish it to run sittings against it.",
        }}
      >
        {items.map((exam) => {
          const locked = exam.owner_kind === "platform" && scope.kind === "org";
          const publishBusy = action.busy === `publish:${exam.id}`;
          return (
            <AuthoringListRow
              key={exam.id}
              title={exam.name}
              meta={`${exam.code} · ${Math.round(exam.default_reading_seconds / 60)} min reading · ${Math.round(exam.default_simulation_seconds / 60)} min station${exam.owner_kind === "platform" ? " · OSCE Guide" : ""}${exam.partner_pilot ? " · partner pilot" : ""}`}
            >
              <StatusBadge status={exam.status} />
              <AuthoringRowActions>
                <AuthoringIconAction
                  label={
                    locked
                      ? "OSCE Guide exams are edited in the staff catalogue"
                      : "Edit"
                  }
                  disabled={locked}
                  onClick={() => {
                    setForm({
                      code: exam.code,
                      name: exam.name,
                      reading: String(exam.default_reading_seconds),
                      simulation: String(exam.default_simulation_seconds),
                      attempts: String(exam.station_attempt_limit),
                      partnerPilot: exam.partner_pilot,
                      rubricVersionId: exam.rubric_version_id ?? "",
                      settings: exam.settings ?? blankExam.settings,
                    });
                    setEditing(exam);
                  }}
                >
                  <HiOutlinePencilSquare className="h-4 w-4" aria-hidden />
                </AuthoringIconAction>
                {/* A retired exam cannot be published again. */}
                {exam.status === "draft" ? (
                  <AuthoringIconAction
                    variant="primary"
                    // The server refuses to publish an exam that names no rubric.
                    label={exam.rubric_version_id ? "Publish" : "Choose a marking scheme version first"}
                    busy={publishBusy}
                    busyLabel="Publishing…"
                    disabled={action.busy !== null || !exam.rubric_version_id}
                    onClick={() =>
                      void action.run(`publish:${exam.id}`, () => publishExam(scope, exam.id))
                    }
                  >
                    <HiOutlineArrowUpTray className="h-4 w-4" aria-hidden />
                  </AuthoringIconAction>
                ) : null}
                {/* Only a published exam can be retired; a draft is simply not offered. */}
                {exam.status === "published" && !locked ? (
                  <AuthoringIconAction
                    variant="warning"
                    label="Retire"
                    disabled={action.busy !== null}
                    onClick={() => setRetiring(exam)}
                  >
                    <HiOutlineNoSymbol className="h-4 w-4" aria-hidden />
                  </AuthoringIconAction>
                ) : null}
                {/* The platform catalogue has no delete: retire is its only exit. */}
                {locked || scope.kind === "platform" ? null : (
                  <AuthoringIconAction
                    variant="danger"
                    label="Delete"
                    disabled={action.busy !== null}
                    onClick={() => setDeleting(exam)}
                  >
                    <HiOutlineTrash className="h-4 w-4" aria-hidden />
                  </AuthoringIconAction>
                )}
              </AuthoringRowActions>
            </AuthoringListRow>
          );
        })}
      </ListCard>

      <AuthoringDialog
        open={creating}
        title="Create exam"
        lead="The code is unique within this organisation only, so two schools may both have a finals."
        error={action.error}
        busy={action.busy === "create"}
        busyLabel="Creating…"
        commitLabel="Create exam"
        commitDisabled={form.code.trim() === "" || form.name.trim() === ""}
        onClose={() => setCreating(false)}
        onCommit={() =>
          void action.run("create", async () => {
            await createExam(scope, {
              code: form.code.trim(),
              name: form.name.trim(),
              default_reading_seconds: Number(form.reading),
              default_simulation_seconds: Number(form.simulation),
              station_attempt_limit: Number(form.attempts),
              partner_pilot: form.partnerPilot,
              rubric_version_id: form.rubricVersionId || null,
              settings: form.settings,
            });
            setCreating(false);
          })
        }
      >
        <ExamFields value={form} onChange={setForm} />
      </AuthoringDialog>

      <AuthoringDialog
        open={editing !== null}
        title="Edit exam"
        lead="Publishing is refused without a marking scheme version."
        busy={action.busy === "edit"}
        busyLabel="Saving…"
        commitLabel="Save"
        commitDisabled={form.name.trim() === ""}
        onClose={() => setEditing(null)}
        onCommit={() =>
          void action.run("edit", async () => {
            if (!editing) return;
            await updateExam(scope, editing.id, {
              name: form.name.trim(),
              default_reading_seconds: Number(form.reading),
              default_simulation_seconds: Number(form.simulation),
              station_attempt_limit: Number(form.attempts),
              partner_pilot: form.partnerPilot,
              rubric_version_id: form.rubricVersionId || null,
              settings: form.settings,
            });
            setEditing(null);
          })
        }
      >
        {editingExam ? (
          <div className="mb-4 space-y-3">
            <StepGuide steps={examSteps(editingExam)} line={examNextAction(editingExam).line} />
          </div>
        ) : null}
        <ExamFields value={form} onChange={setForm} codeDisabled />
      </AuthoringDialog>

      <ConfirmModal
        isOpen={deleting !== null}
        onCancel={() => setDeleting(null)}
        onConfirm={() => {
          if (!deleting) return;
          void action.run(`delete:${deleting.id}`, () => deleteExam(scope, deleting.id)).then((ok) => {
            if (ok) setDeleting(null);
          });
        }}
        isLoading={deleting !== null && action.busy === `delete:${deleting.id}`}
        tone="danger"
        title={deleting ? `Delete "${deleting.name}"?` : "Confirm"}
        confirmText="Delete exam"
        error={action.error}
        message="Only a draft nothing was ever built on can be deleted this way. Anything with a station, a sitting or an attempt against it cannot be deleted. Retire it instead."
      />

      <ConfirmModal
        isOpen={retiring !== null}
        onCancel={() => setRetiring(null)}
        onConfirm={() => {
          if (!retiring) return;
          void action.run(`retire:${retiring.id}`, () => retireExam(scope, retiring.id)).then((ok) => {
            if (ok) setRetiring(null);
          });
        }}
        isLoading={retiring !== null && action.busy === `retire:${retiring.id}`}
        tone="danger"
        title={retiring ? `Retire "${retiring.name}"?` : "Confirm"}
        confirmText="Retire exam"
        error={action.error}
        message="It stops being offered for new practice and sittings, and cannot be published again. What was already attempted against it stays as it is."
      />
    </div>
  );
}
