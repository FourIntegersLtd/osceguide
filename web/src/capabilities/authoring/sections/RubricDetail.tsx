"use client";

import { useState } from "react";
import {
  HiOutlineArchiveBox,
  HiOutlineArrowLeft,
  HiOutlineArrowUpTray,
  HiOutlinePencilSquare,
} from "react-icons/hi2";
import { StructureBuilder } from "@/b2b/components/features/stations/templates/builder/StructureBuilder";
import type { StationStructure } from "@/b2b/types/b2bStationTemplateTypes";
import { Alert, AsyncBoundary } from "@/foundation/ui";
import { AuthoringButton } from "@/capabilities/authoring/parts/AuthoringButton";
import { AuthoringCard } from "@/capabilities/authoring/parts/AuthoringCard";
import {
  AuthoringIconAction,
  AuthoringRowActions,
} from "@/capabilities/authoring/parts/AuthoringIconAction";
import { useAsync } from "@/foundation/hooks";
import {
  addRubricVersion,
  archiveRubricVersion,
  editRubricVersion,
  publishRubricVersion,
  readRubric,
  type Rubric,
  type RubricVersion,
} from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { useAction } from "@/capabilities/authoring/parts/useAction";
import { StatusBadge } from "@/capabilities/authoring/parts/StatusPills";
import { AuthoringDialog } from "@/capabilities/authoring/parts/AuthoringDialog";
import {
  JsonField,
  formatJson,
  jsonProblem,
  parseJson,
} from "@/capabilities/authoring/parts/JsonField";
import {
  emptyMarkingLayout,
  markingLayoutFromVersion,
  markingLayoutToJson,
} from "@/capabilities/authoring/templates/rubricMarkingLayout";

/** A rubric's versions, and the writes against each one. */
export function RubricDetail({ rubricId, onBack }: { rubricId: string; onBack: () => void }) {
  const scope = useAuthoringScope();
  const rubric = useAsync((signal) => readRubric(scope, rubricId, signal), [scope.base, rubricId]);
  const action = useAction(rubric.reload);

  const [editing, setEditing] = useState<RubricVersion | null>(null);
  const [prompt, setPrompt] = useState("");
  const [structure, setStructure] = useState("{}");
  const [pacing, setPacing] = useState("{}");
  const [markingLayout, setMarkingLayout] = useState<StationStructure>(emptyMarkingLayout());

  return (
    <div className="space-y-4">
      <button
        type="button"
        onClick={onBack}
        className="inline-flex items-center gap-1.5 text-osce-body font-medium text-b2b-accent hover:underline"
      >
        <HiOutlineArrowLeft className="h-4 w-4 shrink-0" aria-hidden />
        Rubrics
      </button>

      {action.error ? <Alert tone="danger">{action.error}</Alert> : null}

      <AsyncBoundary state={rubric}>
        {(data: Rubric) => (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-osce-body font-semibold text-b2b-headline">{data.title}</h2>
              <AuthoringButton
                variant="secondary"
                size="sm"
                disabled={action.busy !== null}
                onClick={() => void action.run("add", () => addRubricVersion(scope, data.id))}
              >
                {action.busy === "add" ? "Creating…" : "New draft version"}
              </AuthoringButton>
            </div>

            {(data.versions ?? []).length === 0 ? (
              <AuthoringCard padding="md">
                <p className="text-osce-body text-b2b-mid">
                  This rubric has no versions yet. Cut a draft to start writing it.
                </p>
              </AuthoringCard>
            ) : null}

            {[...(data.versions ?? [])]
              .sort((a, b) => b.version - a.version)
              .map((version) => (
                <AuthoringCard key={version.id} padding="md">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-osce-body font-medium text-b2b-headline">
                        Version {version.version}
                      </p>
                      <p className="mt-0.5 line-clamp-2 text-osce-caption text-b2b-mid">
                        {version.system_prompt || "No system prompt."}
                      </p>
                    </div>
                    <StatusBadge status={version.status} />
                  </div>
                  <div className="mt-3">
                    <AuthoringRowActions>
                      {version.status !== "published" ? (
                        <AuthoringIconAction
                          label="Edit"
                          onClick={() => {
                            setEditing(version);
                            setPrompt(version.system_prompt);
                            setStructure(formatJson(version.structure));
                            setPacing(formatJson(version.pacing));
                            setMarkingLayout(
                              markingLayoutFromVersion(version.marking_layout) ??
                                emptyMarkingLayout(),
                            );
                          }}
                        >
                          <HiOutlinePencilSquare className="h-4 w-4" aria-hidden />
                        </AuthoringIconAction>
                      ) : null}
                      {version.status !== "published" ? (
                        <AuthoringIconAction
                          variant="primary"
                          label="Publish"
                          busy={action.busy === `publish:${version.id}`}
                          busyLabel="Publishing…"
                          disabled={action.busy !== null}
                          onClick={() =>
                            void action.run(`publish:${version.id}`, () =>
                              publishRubricVersion(scope, data.id, version.version),
                            )
                          }
                        >
                          <HiOutlineArrowUpTray className="h-4 w-4" aria-hidden />
                        </AuthoringIconAction>
                      ) : null}
                      {version.status !== "archived" ? (
                        <AuthoringIconAction
                          variant="warning"
                          label="Archive"
                          busy={action.busy === `archive:${version.id}`}
                          busyLabel="Archiving…"
                          disabled={action.busy !== null}
                          onClick={() =>
                            void action.run(`archive:${version.id}`, () =>
                              archiveRubricVersion(scope, data.id, version.version),
                            )
                          }
                        >
                          <HiOutlineArchiveBox className="h-4 w-4" aria-hidden />
                        </AuthoringIconAction>
                      ) : null}
                    </AuthoringRowActions>
                  </div>
                </AuthoringCard>
              ))}

            <AuthoringDialog
              open={editing !== null}
              title={editing ? `Edit version ${editing.version}` : "Edit version"}
              lead="A published version is what attempts were marked against, so it cannot be edited."
              busy={action.busy === "edit"}
              busyLabel="Saving…"
              commitLabel="Save"
              commitDisabled={
                prompt.trim() === "" ||
                jsonProblem(structure) !== null ||
                jsonProblem(pacing) !== null
              }
              onClose={() => setEditing(null)}
              onCommit={() =>
                void action.run("edit", async () => {
                  if (!editing) return;
                  await editRubricVersion(scope, data.id, editing.version, {
                    system_prompt: prompt,
                    structure: parseJson(structure),
                    pacing: parseJson(pacing),
                    marking_layout: markingLayoutToJson(markingLayout),
                  });
                  setEditing(null);
                })
              }
            >
              <div>
                <label className="block text-osce-body font-semibold text-b2b-headline">
                  System prompt
                </label>
                <textarea
                  value={prompt}
                  rows={6}
                  onChange={(e) => setPrompt(e.target.value)}
                  className="mt-1 w-full rounded-md border border-b2b-border bg-white px-3 py-2 text-osce-body text-b2b-headline focus:border-osce-accent focus:outline-none focus:ring-2 focus:ring-osce-accent-subtle"
                />
              </div>
              <JsonField label="Structure" value={structure} onChange={setStructure} />
              <JsonField label="Pacing" rows={6} value={pacing} onChange={setPacing} />
              <div>
                <p className="text-osce-body font-semibold text-b2b-headline">Examiner layout</p>
                <p className="mt-0.5 text-osce-caption text-b2b-mid">
                  Structured fields human reviewers see in slot review. Platform catalogue rubrics
                  need a layout before publish.
                </p>
                <div className="mt-3 rounded-md border border-b2b-border bg-white p-3">
                  <StructureBuilder
                    kind="feedback"
                    value={markingLayout}
                    onChange={setMarkingLayout}
                    title={data.title}
                    flatChrome
                  />
                </div>
              </div>
            </AuthoringDialog>
          </div>
        )}
      </AsyncBoundary>
    </div>
  );
}
