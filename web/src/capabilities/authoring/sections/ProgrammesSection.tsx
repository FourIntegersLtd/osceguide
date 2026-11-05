"use client";

import { useState } from "react";
import { useSurface } from "@/capabilities";
import { HiOutlineAcademicCap, HiOutlineArrowPath, HiOutlineNoSymbol, HiOutlinePlusCircle } from "react-icons/hi2";
import { Alert, Select, TextLink } from "@/foundation/ui";
import { AuthoringButton } from "@/capabilities/authoring/parts/AuthoringButton";
import {
  AuthoringIconAction,
  AuthoringRowActions,
} from "@/capabilities/authoring/parts/AuthoringIconAction";
import { AuthoringListRow } from "@/capabilities/authoring/parts/AuthoringListRow";
import { AuthoringSectionLead } from "@/capabilities/authoring/parts/AuthoringSectionLead";
import { LoadError } from "@/capabilities/authoring/parts/LoadError";
import { useAsync } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import {
  addProgramme,
  listExams,
  listProgrammes,
  updateProgramme,
} from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { useAction } from "@/capabilities/authoring/parts/useAction";
import { ListCard } from "@/capabilities/authoring/parts/ListCard";
import { StatusBadge } from "@/capabilities/authoring/parts/StatusPills";
import { AuthoringDialog } from "@/capabilities/authoring/parts/AuthoringDialog";

/**
 * Programmes: an institution's sittings, grouped under one exam.
 *
 * The exam may be the institution's own or one the platform published; the
 * code is resolved in the institution's scope, so its own wins a clash. There
 * is no platform equivalent — the catalogue has nothing to group — which is
 * why this section is only offered where `supportsProgrammes` holds.
 */
export function ProgrammesSection() {
  const scope = useAuthoringScope();
  const programmes = useAsync((signal) => listProgrammes(scope, signal), [scope.base]);
  const exams = useAsync((signal) => listExams(scope, {}, signal), [scope.base]);
  const action = useAction(programmes.reload);

  const { session } = useSession();
  const { hrefFor } = useSurface();
  const [adding, setAdding] = useState(false);
  const [examCode, setExamCode] = useState("");

  const items = programmes.data?.items ?? [];
  const publishedExams = (exams.data?.items ?? []).filter((exam) => exam.status === "published");

  return (
    <div className="space-y-5">
      <AuthoringSectionLead
        action={
          can(session, "schedule_sittings") ? (
            <div className="flex flex-wrap items-center gap-3">
            <TextLink href={hrefFor("/programmes")} variant="muted" className="text-osce-meta">
              Exams the platform publishes
            </TextLink>
            <AuthoringButton
              variant="commit"
              size="sm"
              className="gap-2"
              onClick={() => setAdding(true)}
            >
              <HiOutlinePlusCircle className="h-4 w-4 shrink-0" aria-hidden />
              New programme
            </AuthoringButton>
            </div>
          ) : null
        }
      >
        A programme groups this institution&apos;s sittings under one exam.
      </AuthoringSectionLead>

      {action.error ? <Alert tone="danger">{action.error}</Alert> : null}

      <ListCard
        count={items.length}
        countLabel="Programmes"
        loading={programmes.loading && !programmes.data}
        error={programmes.error ? programmes.error.message : null}
        onDismissError={programmes.reload}
        empty={{
          title: "No programmes yet",
          description: "Add a programme for each exam you run sittings against.",
        }}
      >
        {items.map((programme) => {
          const active = programme.status === "active";
          // A draft has never been active, so "Reactivate" would say something untrue.
          const switchLabel = active ? "Retire" : programme.status === "draft" ? "Activate" : "Reactivate";
          const statusBusy = action.busy === `status:${programme.id}`;
          return (
            <AuthoringListRow
              key={programme.id}
              leading={
                <span
                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-osce-md bg-surface-raised text-ink-muted"
                  aria-hidden
                >
                  <HiOutlineAcademicCap className="h-4 w-4" />
                </span>
              }
              title={programme.exam_name}
              meta={`${programme.exam_code} · ${programme.source}${programme.exam_owner_kind === "platform" ? " · OSCE Guide exam" : ""}`}
            >
              <StatusBadge status={programme.status} />
              <AuthoringRowActions write>
                <AuthoringIconAction
                  variant={active ? "warning" : "primary"}
                  label={switchLabel}
                  busy={statusBusy}
                  busyLabel="Saving…"
                  disabled={action.busy !== null}
                  onClick={() =>
                    void action.run(`status:${programme.id}`, () =>
                      updateProgramme(scope, programme.id, active ? "retired" : "active"),
                    )
                  }
                >
                  {active ? (
                    <HiOutlineNoSymbol className="h-4 w-4" aria-hidden />
                  ) : (
                    <HiOutlineArrowPath className="h-4 w-4" aria-hidden />
                  )}
                </AuthoringIconAction>
              </AuthoringRowActions>
            </AuthoringListRow>
          );
        })}
      </ListCard>

      <AuthoringDialog
        open={adding}
        title="Add programme"
        lead="Choose the exam. Sittings you schedule for it are grouped under this programme."
        error={action.error}
        busy={action.busy === "add"}
        busyLabel="Adding…"
        commitLabel="Add programme"
        commitDisabled={examCode.trim() === ""}
        onClose={() => setAdding(false)}
        onCommit={() =>
          void action.run("add", async () => {
            await addProgramme(scope, examCode.trim());
            setExamCode("");
            setAdding(false);
          })
        }
      >
        <div>
          <label htmlFor="programmes-section-exam" className="block text-osce-body font-semibold text-ink">Exam</label>
          <Select
            id="programmes-section-exam"
            value={examCode}
            onChange={(e) => setExamCode(e.target.value)}
            className="mt-1"
          >
            <option value="">Select an exam…</option>
            {publishedExams.map((exam) => (
              <option key={exam.id} value={exam.code}>
                {exam.name} ({exam.code})
              </option>
            ))}
          </Select>
          {exams.error ? (
            <LoadError message={`Exams could not be loaded: ${exams.error.message}`} onRetry={exams.reload} />
          ) : publishedExams.length === 0 ? (
            <p className="mt-2 text-osce-caption text-ink-muted">Publish an exam to use it here.</p>
          ) : (
            <p className="mt-2 text-osce-caption text-ink-muted">Only published exams are listed.</p>
          )}
        </div>
      </AuthoringDialog>
    </div>
  );
}
