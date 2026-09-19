"use client";

import { useState } from "react";
import { HiOutlinePlusCircle } from "react-icons/hi2";
import { Alert, Button } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import {
  createExam,
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
import { ExamFields, blankExam, type ExamDraft } from "@/capabilities/authoring/sections/ExamFields";

/**
 * Exams: what an organisation assesses against.
 *
 * An institution writes its own without asking the platform and without
 * picking from a list — its `finals` and another school's are different rows —
 * and the same screen, under the staff scope, writes the platform catalogue.
 * "Drafts only" narrows to the organisation's own rows, which is the backend's
 * `drafts=true` and not a client-side filter.
 */
export function ExamsSection() {
  const scope = useAuthoringScope();
  const [draftsOnly, setDraftsOnly] = useState(false);
  const exams = useAsync(
    (signal) => listExams(scope, { drafts: draftsOnly || undefined }, signal),
    [scope.base, draftsOnly],
  );
  const action = useAction(exams.reload);

  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<ExamDraft>(blankExam);
  const [editing, setEditing] = useState<Exam | null>(null);

  const items = exams.data?.items ?? [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <label className="inline-flex cursor-pointer items-center gap-2 text-osce-body text-b2b-mid">
          <input
            type="checkbox"
            checked={draftsOnly}
            onChange={(e) => setDraftsOnly(e.target.checked)}
            className="h-4 w-4 rounded border-b2b-border"
          />
          Drafts only
        </label>
        <Button
          themeType="b2b"
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
        </Button>
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
            : "Create an exam, attach a rubric version, then publish it to run sittings against it.",
        }}
      >
        {items.map((exam) => (
          <div
            key={exam.id}
            className="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-5"
          >
            <div className="min-w-0 flex-1">
              <p className="truncate text-osce-body font-medium text-b2b-headline">{exam.name}</p>
              <p className="mt-0.5 truncate text-osce-caption text-b2b-mid">
                {exam.code} · {Math.round(exam.default_reading_seconds / 60)} min reading ·{" "}
                {Math.round(exam.default_simulation_seconds / 60)} min station
                {exam.owner_kind === "platform" ? " · OSCE Guide" : ""}
                {exam.partner_pilot ? " · partner pilot" : ""}
              </p>
            </div>
            <div className="flex shrink-0 flex-wrap items-center gap-2">
              <StatusBadge status={exam.status} />
              <Button
                themeType="b2b"
                variant="secondary"
                size="xs"
                disabled={exam.owner_kind === "platform" && scope.kind === "org"}
                onClick={() => {
                  setForm({
                    code: exam.code,
                    name: exam.name,
                    reading: String(exam.default_reading_seconds),
                    simulation: String(exam.default_simulation_seconds),
                    attempts: String(exam.station_attempt_limit),
                    partnerPilot: exam.partner_pilot,
                    rubricVersionId: exam.rubric_version_id ?? "",
                  });
                  setEditing(exam);
                }}
              >
                Edit
              </Button>
              <Button
                themeType="b2b"
                variant="commit"
                size="xs"
                disabled={exam.status === "published" || action.busy !== null}
                onClick={() => void action.run(`publish:${exam.id}`, () => publishExam(scope, exam.id))}
              >
                {action.busy === `publish:${exam.id}` ? "Publishing…" : "Publish"}
              </Button>
              <Button
                themeType="b2b"
                variant="secondary"
                size="xs"
                disabled={exam.status === "retired" || action.busy !== null}
                onClick={() => void action.run(`retire:${exam.id}`, () => retireExam(scope, exam.id))}
              >
                {action.busy === `retire:${exam.id}` ? "Retiring…" : "Retire"}
              </Button>
            </div>
          </div>
        ))}
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
        lead="Publishing is refused without a rubric version."
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
            });
            setEditing(null);
          })
        }
      >
        <ExamFields value={form} onChange={setForm} codeDisabled />
      </AuthoringDialog>
    </div>
  );
}
