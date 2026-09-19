"use client";

import { useState } from "react";
import { HiOutlinePlusCircle } from "react-icons/hi2";
import { Alert, Button, getInputClassName } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import {
  addStationTemplateVersion,
  createStationTemplate,
  editStationTemplateVersion,
  listStationTemplates,
  publishStationTemplate,
  type StationTemplate,
} from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { useAction } from "@/capabilities/authoring/parts/useAction";
import { ListCard } from "@/capabilities/authoring/parts/ListCard";
import { PublishStatusLine } from "@/capabilities/authoring/parts/StatusPills";
import { AuthoringDialog } from "@/capabilities/authoring/parts/AuthoringDialog";
import {
  JsonField,
  formatJson,
  jsonProblem,
  parseJson,
} from "@/capabilities/authoring/parts/JsonField";
import { latestOf } from "@/capabilities/authoring/sections/versions";

/**
 * Station templates: the layout and fields a station is built on.
 *
 * A station cannot be created against an unpublished template, which is why
 * publish is the loudest control on the row and the list says so when nothing
 * is published yet.
 */
export function StationTemplatesSection() {
  const scope = useAuthoringScope();
  const templates = useAsync((signal) => listStationTemplates(scope, signal), [scope.base]);
  const action = useAction(templates.reload);

  const [creating, setCreating] = useState(false);
  const [title, setTitle] = useState("");
  const [examCode, setExamCode] = useState("");
  const [structure, setStructure] = useState("{}");
  const [editing, setEditing] = useState<{ id: string; version: number } | null>(null);
  const [draft, setDraft] = useState("{}");

  const items = templates.data?.items ?? [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-osce-body text-b2b-mid">
          Define layout and fields for clinical stations.
        </p>
        <Button
          themeType="b2b"
          variant="commit"
          size="sm"
          className="gap-2"
          onClick={() => setCreating(true)}
        >
          <HiOutlinePlusCircle className="h-4 w-4 shrink-0" aria-hidden />
          Create station template
        </Button>
      </div>

      {action.error ? <Alert tone="danger">{action.error}</Alert> : null}

      <ListCard
        count={items.length}
        countLabel="Station templates"
        loading={templates.loading && !templates.data}
        error={templates.error ? templates.error.message : null}
        onDismissError={templates.reload}
        empty={{
          title: "No station templates",
          description:
            "Create a station template, publish it, then use it when building stations.",
        }}
      >
        {items.map((template) => (
          <TemplateRow
            key={template.id}
            template={template}
            busy={action.busy}
            onAddVersion={() =>
              void action.run(`add:${template.id}`, () =>
                addStationTemplateVersion(scope, template.id),
              )
            }
            onPublish={() =>
              void action.run(`publish:${template.id}`, () =>
                publishStationTemplate(scope, template.id),
              )
            }
            onEdit={(version, current) => {
              setEditing({ id: template.id, version });
              setDraft(formatJson(current));
            }}
          />
        ))}
      </ListCard>

      <AuthoringDialog
        open={creating}
        title="Create station template"
        lead="Define layout and fields for clinical stations."
        error={action.error}
        busy={action.busy === "create"}
        busyLabel="Creating…"
        commitLabel="Create template"
        commitDisabled={title.trim() === "" || jsonProblem(structure) !== null}
        onClose={() => setCreating(false)}
        onCommit={() =>
          void action.run("create", async () => {
            await createStationTemplate(scope, {
              title: title.trim(),
              exam_code: examCode.trim() || null,
              structure: parseJson(structure),
            });
            setTitle("");
            setExamCode("");
            setStructure("{}");
            setCreating(false);
          })
        }
      >
        <div>
          <label className="block text-osce-body font-semibold text-b2b-headline">Title</label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className={`mt-1 ${getInputClassName()}`}
            placeholder="e.g. Counselling station"
          />
        </div>
        <div>
          <label className="block text-osce-body font-semibold text-b2b-headline">
            Exam code (optional)
          </label>
          <input
            value={examCode}
            onChange={(e) => setExamCode(e.target.value)}
            className={`mt-1 ${getInputClassName()}`}
            placeholder="Leave blank for any exam"
          />
        </div>
        <JsonField label="Structure" value={structure} onChange={setStructure} />
      </AuthoringDialog>

      <AuthoringDialog
        open={editing !== null}
        title="Edit station template"
        lead="A published version cannot be edited. Cut a new draft first."
        busy={action.busy === "edit"}
        busyLabel="Saving…"
        commitLabel="Save"
        commitDisabled={jsonProblem(draft) !== null}
        onClose={() => setEditing(null)}
        onCommit={() =>
          void action.run("edit", async () => {
            if (!editing) return;
            await editStationTemplateVersion(scope, editing.id, editing.version, parseJson(draft));
            setEditing(null);
          })
        }
      >
        <JsonField
          label="Structure"
          hint={editing ? `Version ${editing.version}.` : undefined}
          value={draft}
          rows={14}
          onChange={setDraft}
        />
      </AuthoringDialog>
    </div>
  );
}

function TemplateRow({
  template,
  busy,
  onAddVersion,
  onPublish,
  onEdit,
}: {
  template: StationTemplate;
  busy: string | null;
  onAddVersion: () => void;
  onPublish: () => void;
  onEdit: (version: number, structure: unknown) => void;
}) {
  const { published, draft, archivedOnly } = latestOf(template.versions);

  return (
    <div className="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-5">
      <div className="min-w-0 flex-1">
        <p className="truncate text-osce-body font-medium text-b2b-headline">{template.title}</p>
        <PublishStatusLine
          kindLabel={template.exam_code}
          published={published}
          draft={draft}
          archivedOnly={archivedOnly}
        />
      </div>
      <div className="flex shrink-0 flex-wrap items-center gap-1">
        <Button
          themeType="b2b"
          variant="secondary"
          size="xs"
          disabled={busy !== null}
          onClick={onAddVersion}
        >
          {busy === `add:${template.id}` ? "Creating…" : "New draft"}
        </Button>
        <Button
          themeType="b2b"
          variant="secondary"
          size="xs"
          disabled={!draft}
          onClick={() => draft && onEdit(draft.version, draft.structure)}
        >
          Edit
        </Button>
        <Button
          themeType="b2b"
          variant="commit"
          size="xs"
          disabled={!draft || busy !== null}
          onClick={onPublish}
        >
          {busy === `publish:${template.id}` ? "Publishing…" : "Publish"}
        </Button>
      </div>
    </div>
  );
}
