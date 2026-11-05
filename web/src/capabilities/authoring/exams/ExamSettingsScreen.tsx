"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Alert, AsyncBoundary, B2CPageHeader, Button, Panel, StepGuide } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { listExams, updateExam, type Exam } from "@/capabilities/authoring/api";
import { staleRefusal } from "@/capabilities/authoring/api/stale";
import { RequireAuthor } from "@/capabilities/authoring/parts/RequireAuthor";
import { useAction } from "@/capabilities/authoring/parts/useAction";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { examDetailPath, examsListPath } from "@/capabilities/authoring/exams/paths";
import { ExamFields, examToDraft, type ExamDraft } from "@/capabilities/authoring/sections/ExamFields";
import { examNextAction, examSteps } from "@/capabilities/authoring/sections/examSteps";

/** Every setting an exam has, as a page: timings, marking scheme, what trainees get after a station. */
export function ExamSettingsScreen({ examId }: { examId: string }) {
  const scope = useAuthoringScope();
  const exams = useAsync((signal) => listExams(scope, { status: "all" }, signal), [scope.base]);
  return (
    <RequireAuthor>
      <AsyncBoundary state={exams}>
        {(page) => {
          const exam = page.items.find((item) => item.id === examId);
          return exam ? (
            <Form exam={exam} reload={exams.reload} />
          ) : (
            <Alert tone="danger">This exam could not be found. It may have been deleted.</Alert>
          );
        }}
      </AsyncBoundary>
    </RequireAuthor>
  );
}

function Form({ exam, reload }: { exam: Exam; reload: () => void }) {
  const scope = useAuthoringScope();
  const { hrefFor } = useSurface();
  const router = useRouter();
  const action = useAction(reload);
  const [form, setForm] = useState<ExamDraft>(() => examToDraft(exam));
  const locked = exam.owner_kind === "platform" && scope.kind === "org";
  // The form's scheme, not the stored one, so the rail follows the pick.
  const state = { status: exam.status, rubric_version_id: form.rubricVersionId };

  function save() {
    void action.run("save", async () => {
      try {
        await updateExam(scope, exam.id, {
          revision: exam.revision,
          name: form.name.trim(),
          default_reading_seconds: Number(form.reading),
          default_simulation_seconds: Number(form.simulation),
          station_attempt_limit: Number(form.attempts),
          partner_pilot: form.partnerPilot,
          rubric_version_id: form.rubricVersionId || null,
          settings: form.settings,
        });
      } catch (cause) {
        const stale = staleRefusal(cause, "exam");
        if (!stale) throw cause;
        // Reloaded, the form reads their version.
        reload();
        throw stale;
      }
      router.push(examDetailPath(hrefFor, exam.id));
    });
  }

  return (
    <div className="flex flex-col gap-6">
      <B2CPageHeader
        eyebrow={exam.name}
        title="Exam settings"
        subtitle="Every setting an exam has: its timings, how it is marked, and what trainees get after a station."
        back={{ href: examsListPath(hrefFor), label: "Exams" }}
      />
      {locked ? <Alert tone="info">OSCE Guide exams are edited in the staff catalogue.</Alert> : null}
      <StepGuide steps={examSteps(state)} line={examNextAction(state).line} />
      <Panel className="flex flex-col gap-4">
        <ExamFields value={form} onChange={setForm} codeDisabled />
        {action.error ? <Alert tone="danger">{action.error}</Alert> : null}
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={() => router.push(examsListPath(hrefFor))} disabled={action.busy !== null}>
            Cancel
          </Button>
          <Button
            variant="primary"
            disabled={locked || action.busy !== null || form.name.trim() === ""}
            onClick={save}
          >
            {action.busy === "save" ? "Saving…" : "Save"}
          </Button>
        </div>
      </Panel>
    </div>
  );
}
