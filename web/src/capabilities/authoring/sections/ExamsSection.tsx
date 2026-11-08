"use client";

import { useAssessWords } from "@/capabilities/assess-words";
import { examChipLabel, examEmptyBody } from "@/capabilities/authoring/lib/authoringCopy";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  HiOutlineArrowUpTray,
  HiOutlineNoSymbol,
  HiOutlinePencilSquare,
  HiOutlinePlusCircle,
  HiOutlineTrash,
} from "react-icons/hi2";
import { Alert, Checkbox, StepGuide, TextLink } from "@/foundation/ui";
import { BoardChip, boardActs, boardStack } from "@/capabilities/authoring/parts/boardUi";
import { useSurface } from "@/capabilities";
import { useCanAuthor } from "@/capabilities/authoring/hooks/useCanAuthor";
import { ExamConfirm } from "@/capabilities/authoring/exams/ExamConfirms";
import { examDetailPath, examNewPath, examSettingsPath } from "@/capabilities/authoring/exams/paths";
import { saveExam } from "@/capabilities/authoring/exams/offer";
import { createWithFreshCode, toMinutes } from "@/capabilities/authoring/exams/newExam";
import { isPlatformError } from "@/foundation/platform-client/errors";
import { programmeFor } from "@/capabilities/authoring/sections/examSteps";
import { examKind, examMetaWithKind } from "@/capabilities/authoring/exams/examKind";
import { AuthoringButton } from "@/capabilities/authoring/parts/AuthoringButton";
import {
  AuthoringIconAction,
  AuthoringRowActions,
} from "@/capabilities/authoring/parts/AuthoringIconAction";
import { AuthoringActionMenu } from "@/capabilities/authoring/parts/AuthoringActionMenu";
import { AuthoringListRow } from "@/capabilities/authoring/parts/AuthoringListRow";
import { useAsync } from "@/foundation/hooks";
import {
  createExam,
  listExams,
  listAllProgrammes,
  listAllSittings,
  publishExam,
  type Exam,
  type Programme,
} from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { useAction } from "@/capabilities/authoring/parts/useAction";
import { ListCard } from "@/capabilities/authoring/parts/ListCard";
import { StatusBadge } from "@/capabilities/authoring/parts/StatusPills";
import { AuthoringDialog } from "@/capabilities/authoring/parts/AuthoringDialog";
import { examChip, examNextAction, examSteps } from "@/capabilities/authoring/sections/examSteps";
import { ExamFields, blankExam, examToDraft, type ExamDraft } from "@/capabilities/authoring/sections/ExamFields";
import { boardBtn } from "@/foundation/ui/boardKit";

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
  const w = useAssessWords();
  const [draftsOnly, setDraftsOnly] = useState(false);
  const exams = useAsync(
    (signal) => listExams(scope, { status: draftsOnly ? "draft" : "all" }, signal),
    [scope.base, draftsOnly],
  );
  const { hrefFor } = useSurface();
  const router = useRouter();
  const canAuthor = useCanAuthor();
  const org = scope.kind === "org";
  // Programmes say which exams are offered for scheduling; the staff catalogue has none.
  const programmes = useAsync(
    async (signal) => (org ? listAllProgrammes(scope, signal) : []),
    [scope.base, org],
  );
  // An employer's row names the exam's kind, which only its assessments carry.
  const sittings = useAsync(
    async (signal) => (org && w.hiring ? await listAllSittings(scope, signal) : []),
    [scope.base, org, w.hiring],
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
    <div className={org ? boardStack : "space-y-4"}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Checkbox
          checked={draftsOnly}
          onChange={(e) => setDraftsOnly(e.target.checked)}
          label="Drafts only"
          className={org ? undefined : "items-center"}
        />
        <div className={org ? boardActs : "flex flex-wrap items-center gap-3"}>
          {org && canAuthor ? (
            <Link href={hrefFor("/programmes")} className={boardBtn()}>
              Adopt from OSCE Guide
            </Link>
          ) : null}
          {org ? (
            canAuthor ? (
              <Link href={examNewPath(hrefFor)} className={boardBtn("primary")}>
                Create exam
              </Link>
            ) : null
          ) : (
            <AuthoringButton
              write
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
          )}
        </div>
      </div>

      {action.error ? <Alert tone="danger">{action.error}</Alert> : null}
      {programmes.error ? (
        <Alert tone="danger">Which exams are ready to schedule could not be loaded. Reload the page to try again.</Alert>
      ) : null}

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
            : examEmptyBody(w),
          sameForReaders: draftsOnly,
        }}
      >
        {items.map((exam) => {
          const locked = exam.owner_kind === "platform" && scope.kind === "org";
          const publishBusy = action.busy === `publish:${exam.id}`;
          return (
            <AuthoringListRow
              key={exam.id}
              title={exam.name}
              onOpen={org ? () => router.push(examDetailPath(hrefFor, exam.id)) : undefined}
              meta={examMetaWithKind(
                `${exam.code} · ${toMinutes(exam.default_reading_seconds)} min reading · ${toMinutes(exam.default_simulation_seconds)} min station${exam.owner_kind === "platform" ? " · OSCE Guide" : ""}${exam.partner_pilot ? " · partner pilot" : ""}`,
                programmes.data && sittings.data ? examKind(exam.id, programmes.data, sittings.data) : null,
                w,
              )}
            >
              <StatusBadge status={exam.status} />
              {org && programmes.data ? <ExamChipBadge exam={exam} programmes={programmes.data} /> : null}
              <AuthoringRowActions write>
                <AuthoringIconAction
                  label={
                    locked
                      ? "OSCE Guide exams are edited in the staff catalogue"
                      : "Edit"
                  }
                  text="Edit"
                  disabled={locked}
                  onClick={() => {
                    setForm(examToDraft(exam));
                    setEditing(exam);
                  }}
                >
                  <HiOutlinePencilSquare className="h-4 w-4" aria-hidden />
                </AuthoringIconAction>
                <AuthoringActionMenu
                  label={`Actions for ${exam.name}`}
                  items={[
                    // A retired exam cannot be published again; the server refuses one that names no rubric.
                    exam.status === "draft" && {
                      label: publishBusy ? "Publishing…" : "Publish",
                      icon: <HiOutlineArrowUpTray className="h-4 w-4" />,
                      disabled: action.busy !== null || !exam.rubric_version_id,
                      hint: exam.rubric_version_id ? undefined : "Choose a marking scheme version first",
                      onSelect: () => void action.run(`publish:${exam.id}`, () => publishExam(scope, exam.id)),
                    },
                    // Only a published exam can be retired; a draft is simply not offered.
                    exam.status === "published" && !locked && {
                      label: "Retire",
                      icon: <HiOutlineNoSymbol className="h-4 w-4" />,
                      disabled: action.busy !== null,
                      onSelect: () => setRetiring(exam),
                    },
                    // The platform catalogue has no delete: retire is its only exit.
                    !locked && scope.kind !== "platform" && {
                      label: "Delete",
                      icon: <HiOutlineTrash className="h-4 w-4" />,
                      tone: "danger" as const,
                      disabled: action.busy !== null,
                      onSelect: () => setDeleting(exam),
                    },
                  ]}
                />
              </AuthoringRowActions>
            </AuthoringListRow>
          );
        })}
      </ListCard>

      <AuthoringDialog
        open={creating}
        title="Create exam"
        error={action.error}
        busy={action.busy === "create"}
        busyLabel="Creating…"
        commitLabel="Create exam"
        commitDisabled={form.name.trim() === ""}
        onClose={() => setCreating(false)}
        onCommit={() =>
          void action.run("create", async () => {
            await createWithFreshCode(
              form.name,
              (cause) => isPlatformError(cause) && cause.status === 409,
              (code) =>
                createExam(scope, {
                  code,
                  name: form.name.trim(),
                  default_reading_seconds: Number(form.reading),
                  default_simulation_seconds: Number(form.simulation),
                  station_attempt_limit: Number(form.attempts),
                  partner_pilot: form.partnerPilot,
                  rubric_version_id: form.rubricVersionId || null,
                  settings: form.settings,
                }),
            );
            setCreating(false);
          })
        }
      >
        <ExamFields value={form} onChange={setForm} />
      </AuthoringDialog>

      <AuthoringDialog
        open={editing !== null}
        title="Edit exam"
        lead={w.hiring ? "Choose a marking scheme version for this exam, then publish." : "Publishing is refused without a marking scheme version."}
        busy={action.busy === "edit"}
        busyLabel="Saving…"
        commitLabel="Save"
        commitDisabled={form.name.trim() === ""}
        onClose={() => setEditing(null)}
        onCommit={() =>
          void action.run("edit", async () => {
            if (!editing) return;
            await saveExam(
              scope,
              editing,
              {
                name: form.name.trim(),
                default_reading_seconds: Number(form.reading),
                default_simulation_seconds: Number(form.simulation),
                station_attempt_limit: Number(form.attempts),
                partner_pilot: form.partnerPilot,
                rubric_version_id: form.rubricVersionId || null,
                settings: form.settings,
              },
              // Close the form: reopened, it reads their version.
              () => {
                setEditing(null);
                exams.reload();
              },
            );
            setEditing(null);
          })
        }
      >
        {editing && org ? (
          <TextLink href={examSettingsPath(hrefFor, editing.id)} variant="muted" className="mb-3 inline-block text-osce-meta">
            Open the full form ›
          </TextLink>
        ) : null}
        {editingExam ? (
          <div className="mb-4 space-y-3">
            <StepGuide steps={examSteps(editingExam)} line={examNextAction(editingExam).line} />
          </div>
        ) : null}
        <ExamFields value={form} onChange={setForm} codeDisabled />
      </AuthoringDialog>

      <ExamConfirm kind="delete" scope={scope} exam={deleting} action={action} onCancel={() => setDeleting(null)} />
      <ExamConfirm kind="retire" scope={scope} exam={retiring} action={action} onCancel={() => setRetiring(null)} />
    </div>
  );
}

function ExamChipBadge({ exam, programmes }: { exam: Exam; programmes: Programme[] }) {
  const w = useAssessWords();
  const chip = examChip(exam, programmeFor(programmes, exam));
  return (
    <BoardChip tone={chip === "Ready to schedule" ? "info" : "warn"}>{examChipLabel(chip, w)}</BoardChip>
  );
}
