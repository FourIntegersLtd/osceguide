"use client";

import { useState } from "react";
import { HiOutlineArrowLeft } from "react-icons/hi2";
import { Alert, AsyncBoundary, Button, Card } from "@/foundation/ui";
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

/** A rubric's versions, and the writes against each one. */
export function RubricDetail({ rubricId, onBack }: { rubricId: string; onBack: () => void }) {
  const scope = useAuthoringScope();
  const rubric = useAsync((signal) => readRubric(scope, rubricId, signal), [scope.base, rubricId]);
  const action = useAction(rubric.reload);

  const [editing, setEditing] = useState<RubricVersion | null>(null);
  const [prompt, setPrompt] = useState("");
  const [structure, setStructure] = useState("{}");
  const [pacing, setPacing] = useState("{}");

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
              <Button
                themeType="b2b"
                variant="secondary"
                size="sm"
                disabled={action.busy !== null}
                onClick={() => void action.run("add", () => addRubricVersion(scope, data.id))}
              >
                {action.busy === "add" ? "Creating…" : "New draft version"}
              </Button>
            </div>

            {(data.versions ?? []).length === 0 ? (
              <Card themeType="b2b" padding="md">
                <p className="text-osce-body text-b2b-mid">
                  This rubric has no versions yet. Cut a draft to start writing it.
                </p>
              </Card>
            ) : null}

            {[...(data.versions ?? [])]
              .sort((a, b) => b.version - a.version)
              .map((version) => (
                <Card key={version.id} themeType="b2b" padding="md">
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
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <Button
                      themeType="b2b"
                      variant="secondary"
                      size="xs"
                      disabled={version.status === "published"}
                      onClick={() => {
                        setEditing(version);
                        setPrompt(version.system_prompt);
                        setStructure(formatJson(version.structure));
                        setPacing(formatJson(version.pacing));
                      }}
                    >
                      Edit
                    </Button>
                    <Button
                      themeType="b2b"
                      variant="commit"
                      size="xs"
                      disabled={version.status === "published" || action.busy !== null}
                      onClick={() =>
                        void action.run(`publish:${version.id}`, () =>
                          publishRubricVersion(scope, data.id, version.version),
                        )
                      }
                    >
                      {action.busy === `publish:${version.id}` ? "Publishing…" : "Publish"}
                    </Button>
                    <Button
                      themeType="b2b"
                      variant="secondary"
                      size="xs"
                      disabled={version.status === "archived" || action.busy !== null}
                      onClick={() =>
                        void action.run(`archive:${version.id}`, () =>
                          archiveRubricVersion(scope, data.id, version.version),
                        )
                      }
                    >
                      {action.busy === `archive:${version.id}` ? "Archiving…" : "Archive"}
                    </Button>
                  </div>
                </Card>
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
            </AuthoringDialog>
          </div>
        )}
      </AsyncBoundary>
    </div>
  );
}
