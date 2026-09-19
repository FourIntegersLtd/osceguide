"use client";

import { useMemo, useState } from "react";
import { HiOutlinePlusCircle } from "react-icons/hi2";
import { Alert, Button, getInputClassName } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import {
  addFeedbackTemplateVersion,
  createFeedbackTemplate,
  editFeedbackTemplateVersion,
  listFeedbackTemplates,
  listRubrics,
  publishFeedbackTemplate,
  type FeedbackTemplate,
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
 * Feedback templates: which of a rubric's fields an examiner is asked for.
 *
 * A template is a selection over a published rubric version, so the create
 * dialog offers the rubric versions rather than a free-text id — picking the
 * wrong one is the mistake the old wizard's third step existed to prevent.
 */
export function FeedbackTemplatesSection() {
  const scope = useAuthoringScope();
  const templates = useAsync((signal) => listFeedbackTemplates(scope, signal), [scope.base]);
  const rubrics = useAsync((signal) => listRubrics(scope, {}, signal), [scope.base]);
  const action = useAction(templates.reload);

  const [creating, setCreating] = useState(false);
  const [title, setTitle] = useState("");
  const [rubricVersionId, setRubricVersionId] = useState("");
  const [selection, setSelection] = useState("{}");
  const [editing, setEditing] = useState<{ id: string; version: number } | null>(null);
  const [draft, setDraft] = useState("{}");

  const items = templates.data?.items ?? [];
  const rubricVersions = useMemo(
    () =>
      (rubrics.data?.items ?? []).flatMap((rubric) =>
        (rubric.versions ?? []).map((v) => ({
          id: v.id,
          label: `${rubric.title} · v${v.version}${v.status === "published" ? "" : ` (${v.status})`}`,
        })),
      ),
    [rubrics.data],
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-osce-body text-b2b-mid">
          Define examiner marking structure for live sessions.
        </p>
        <Button
          themeType="b2b"
          variant="commit"
          size="sm"
          className="gap-2"
          onClick={() => setCreating(true)}
        >
          <HiOutlinePlusCircle className="h-4 w-4 shrink-0" aria-hidden />
          Create feedback template
        </Button>
      </div>

      {action.error ? <Alert tone="danger">{action.error}</Alert> : null}

      <ListCard
        count={items.length}
        countLabel="Feedback templates"
        loading={templates.loading && !templates.data}
        error={templates.error ? templates.error.message : null}
        onDismissError={templates.reload}
        empty={{
          title: "No feedback templates",
          description:
            "Publish a feedback template before scheduling live sessions — examiners need a marking structure.",
        }}
      >
        {items.map((template) => (
          <FeedbackRow
            key={template.id}
            template={template}
            busy={action.busy}
            onAddVersion={() =>
              void action.run(`add:${template.id}`, () =>
                addFeedbackTemplateVersion(scope, template.id),
              )
            }
            onPublish={() =>
              void action.run(`publish:${template.id}`, () =>
                publishFeedbackTemplate(scope, template.id),
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
        title="Create feedback template"
        lead="Pick the rubric version examiners will mark against, then choose its fields."
        error={action.error}
        busy={action.busy === "create"}
        busyLabel="Creating…"
        commitLabel="Create template"
        commitDisabled={
          title.trim() === "" || rubricVersionId === "" || jsonProblem(selection) !== null
        }
        onClose={() => setCreating(false)}
        onCommit={() =>
          void action.run("create", async () => {
            await createFeedbackTemplate(scope, {
              title: title.trim(),
              rubric_version_id: rubricVersionId,
              field_selection: parseJson(selection),
            });
            setTitle("");
            setRubricVersionId("");
            setSelection("{}");
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
            placeholder="e.g. Examiner marking sheet"
          />
        </div>
        <div>
          <label className="block text-osce-body font-semibold text-b2b-headline">
            Rubric version
          </label>
          <select
            value={rubricVersionId}
            onChange={(e) => setRubricVersionId(e.target.value)}
            className="mt-1 w-full rounded-md border border-b2b-border bg-white px-3 py-2 text-osce-body text-b2b-headline"
          >
            <option value="">Select a rubric version…</option>
            {rubricVersions.map((choice) => (
              <option key={choice.id} value={choice.id}>
                {choice.label}
              </option>
            ))}
          </select>
        </div>
        <JsonField label="Field selection" value={selection} onChange={setSelection} />
      </AuthoringDialog>

      <AuthoringDialog
        open={editing !== null}
        title="Edit feedback template"
        lead="A published version cannot be edited. Cut a new draft first."
        busy={action.busy === "edit"}
        busyLabel="Saving…"
        commitLabel="Save"
        commitDisabled={jsonProblem(draft) !== null}
        onClose={() => setEditing(null)}
        onCommit={() =>
          void action.run("edit", async () => {
            if (!editing) return;
            await editFeedbackTemplateVersion(scope, editing.id, editing.version, parseJson(draft));
            setEditing(null);
          })
        }
      >
        <JsonField
          label="Field selection"
          hint={editing ? `Version ${editing.version}.` : undefined}
          value={draft}
          rows={14}
          onChange={setDraft}
        />
      </AuthoringDialog>
    </div>
  );
}

function FeedbackRow({
  template,
  busy,
  onAddVersion,
  onPublish,
  onEdit,
}: {
  template: FeedbackTemplate;
  busy: string | null;
  onAddVersion: () => void;
  onPublish: () => void;
  onEdit: (version: number, selection: unknown) => void;
}) {
  const { published, draft, archivedOnly } = latestOf(template.versions);

  return (
    <div className="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-5">
      <div className="min-w-0 flex-1">
        <p className="truncate text-osce-body font-medium text-b2b-headline">{template.title}</p>
        <PublishStatusLine
          kindLabel={template.owner_kind === "platform" ? "OSCE Guide" : null}
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
          onClick={() => draft && onEdit(draft.version, draft.field_selection)}
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
