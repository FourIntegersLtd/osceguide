"use client";

import { useCanAuthor } from "@/capabilities/authoring/hooks/useCanAuthor";
import { useId, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Alert, AsyncBoundary, B2CPageHeader, cn, getInputClassName } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { addRubricVersion, copyRubric, readRubric, renameRubric, type Rubric } from "@/capabilities/authoring/api";
import { AuthoringButton } from "@/capabilities/authoring/parts/AuthoringButton";
import { nextRubricTitle } from "@/capabilities/authoring/rubrics/rubricTitle";
import { StatusBadge } from "@/capabilities/authoring/parts/StatusPills";
import { useAction } from "@/capabilities/authoring/parts/useAction";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import type { RubricDashboardPreview } from "@/capabilities/authoring/rubrics/dashboardSlot";
import { RubricBuilder } from "@/capabilities/authoring/rubrics/RubricBuilder";
import { examResumePath, rubricEditPath, rubricsListPath } from "@/capabilities/authoring/templates/paths";

/**
 * The rubric builder's page: loads the rubric, finds the version in the URL
 * and hands it to `RubricBuilder`.
 *
 * Only a draft of a rubric this scope owns is editable. Anything else is
 * shown read-only with the one way forward: a new draft version of your own
 * rubric, or a copy of someone else's.
 */
export function RubricBuilderScreen({
  rubricId,
  version,
  dashboardPreview,
}: {
  rubricId: string;
  version: number;
  dashboardPreview?: RubricDashboardPreview;
}) {
  const scope = useAuthoringScope();
  const { hrefFor } = useSurface();
  const rubric = useAsync((signal) => readRubric(scope, rubricId, signal), [scope.base, rubricId]);
  const canAuthor = useCanAuthor();
  // Set when the New exam sheet sent the author here: publishing offers the way back to it.
  const examId = useSearchParams().get("exam");
  const examHref = examId ? examResumePath(hrefFor, examId) : null;

  return (
    <div className="flex w-full flex-col gap-4 pb-8">
      {examHref ? (
        <Link href={examHref} className="text-osce-body font-medium text-accent hover:underline">
          Close and go back to the exam
        </Link>
      ) : null}
      <AsyncBoundary state={rubric}>
        {(data: Rubric) => {
          const found = (data.versions ?? []).find((candidate) => candidate.version === version);
          // An organisation lists the platform's rubrics too, but may only copy them.
          const owned = !(scope.kind === "org" && data.owner_kind === "platform");
          // Only an author, on a rubric the workspace owns, changes it.
          const editable = owned && canAuthor;
          return (
            <>
              <B2CPageHeader
                title={editable ? <RubricTitle rubric={data} onRenamed={rubric.reload} /> : data.title}
                subtitle={`Marking scheme · version ${version}${owned ? "" : " · OSCE Guide catalogue"}`}
                back={{ href: rubricsListPath(hrefFor), label: "Marking schemes" }}
                action={found ? <VersionActions rubric={data} version={version} status={found.status} owned={owned} examId={examId} /> : undefined}
                className="mb-0"
              />
              {found ? (
                <RubricBuilder
                  // A publish changes what may be edited, and a save by someone else changes what is
                  // there: either way the builder starts over on the reloaded version.
                  key={`${found.id}:${found.status}:${found.revision}`}
                  scope={scope}
                  rubric={data}
                  version={found}
                  readOnly={!editable || found.status !== "draft"}
                  dashboardPreview={dashboardPreview}
                  examHref={examHref}
                  onPublished={rubric.reload}
                  onStale={rubric.reload}
                />
              ) : (
                <Alert tone="warning">This marking scheme has no version {version}.</Alert>
              )}
            </>
          );
        }}
      </AsyncBoundary>
    </div>
  );
}

/**
 * The rubric's title, in place of the header's plain text: click it to rename
 * (R-7). A rubric's title is set once at creation and kept across every
 * version, so renaming it here does not touch the version being edited.
 */
function RubricTitle({ rubric, onRenamed }: { rubric: Rubric; onRenamed: () => void }) {
  const inputId = useId();
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(rubric.title);
  const scope = useAuthoringScope();
  const action = useAction();

  if (!editing) {
    return (
      <button
        type="button"
        onClick={() => {
          setValue(rubric.title);
          setEditing(true);
        }}
        className="text-left hover:underline"
        title="Rename this marking scheme"
      >
        {rubric.title}
      </button>
    );
  }

  const cancel = () => setEditing(false);
  const save = () => {
    const title = nextRubricTitle(rubric.title, value);
    if (title === null) {
      cancel();
      return;
    }
    void action.run("rename", async () => {
      await renameRubric(scope, rubric.id, title);
      onRenamed();
      setEditing(false);
    });
  };

  return (
    <div className="flex items-center gap-2">
      <label htmlFor={inputId} className="sr-only">
        Marking scheme title
      </label>
      <input
        id={inputId}
        ref={(node) => node?.focus()}
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") save();
          if (event.key === "Escape") cancel();
        }}
        onBlur={save}
        className={cn(getInputClassName({ size: "sm" }), "max-w-sm")}
        disabled={action.busy === "rename"}
      />
      {action.error ? <span className="text-osce-caption text-osce-danger">{action.error}</span> : null}
    </div>
  );
}

/** The status, and the way to change a version that can no longer be edited. */
function VersionActions({ rubric, version, status, owned, examId }: { rubric: Rubric; version: number; status: string; owned: boolean; examId: string | null }) {
  const scope = useAuthoringScope();
  const { hrefFor } = useSurface();
  const router = useRouter();
  const action = useAction();
  const draft = (rubric.versions ?? []).find((candidate) => candidate.status === "draft");
  const hasDraft = draft !== undefined;
  return (
    <div className="flex flex-wrap items-center gap-2">
      <StatusBadge status={status} />
      {owned && status !== "draft" && !hasDraft ? (
        <AuthoringButton
          write
          variant="secondary"
          size="sm"
          isLoading={action.busy === "add"}
          onClick={() =>
            action.run("add", async () => {
              const created = await addRubricVersion(scope, rubric.id);
              router.push(rubricEditPath(hrefFor, rubric.id, created.version, examId));
            })
          }
        >
          New draft version
        </AuthoringButton>
      ) : null}
      {owned && draft && draft.version !== version ? (
        <AuthoringButton write variant="secondary" size="sm" onClick={() => router.push(rubricEditPath(hrefFor, rubric.id, draft.version))}>
          Open draft version {draft.version}
        </AuthoringButton>
      ) : null}
      {!owned ? (
        <AuthoringButton
          write
          variant="secondary"
          size="sm"
          isLoading={action.busy === "copy"}
          onClick={() =>
            action.run("copy", async () => {
              const copy = await copyRubric(scope, { source_rubric_id: rubric.id, source_version: version });
              const first = (copy.versions ?? [])[0];
              router.push(rubricEditPath(hrefFor, copy.id, first?.version ?? 1, examId));
            })
          }
        >
          Copy to my marking schemes
        </AuthoringButton>
      ) : null}
      {action.error ? <span className="text-osce-caption text-osce-danger">{action.error}</span> : null}
    </div>
  );
}
