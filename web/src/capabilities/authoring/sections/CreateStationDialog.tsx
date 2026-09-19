"use client";

import { useMemo, useState } from "react";
import { useAsync } from "@/foundation/hooks";
import { getInputClassName } from "@/foundation/ui";
import {
  createStation,
  listExams,
  type StationTemplate,
} from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { useAction } from "@/capabilities/authoring/parts/useAction";
import { AuthoringDialog } from "@/capabilities/authoring/parts/AuthoringDialog";
import { JsonField, jsonProblem, parseJson } from "@/capabilities/authoring/parts/JsonField";

/**
 * Create a station from a published template.
 *
 * The old modal offered "Manual" and "Generate with AI" as two tabs. The
 * generator has no endpoint on this backend — see `docs/port-gaps.md` — so
 * what is here is the manual half, which is the half that wrote the station.
 */
export function CreateStationDialog({
  open,
  templates,
  onClose,
  onCreated,
}: {
  open: boolean;
  templates: StationTemplate[];
  onClose: () => void;
  onCreated: () => void;
}) {
  const scope = useAuthoringScope();
  const [title, setTitle] = useState("");
  const [examCode, setExamCode] = useState("");
  const [templateKey, setTemplateKey] = useState("");
  const [content, setContent] = useState("{}");
  const action = useAction();

  const exams = useAsync((signal) => listExams(scope, {}, signal), [scope.base]);

  const choices = useMemo(
    () =>
      templates.flatMap((t) =>
        t.versions
          .filter((v) => v.status === "published")
          .map((v) => ({ id: v.id, label: `${t.title} (v${v.version})` })),
      ),
    [templates],
  );

  const ready = title.trim() !== "" && examCode !== "" && jsonProblem(content) === null;

  return (
    <AuthoringDialog
      open={open}
      title="Create station"
      lead="Choose a published template, then fill in the station content."
      error={action.error}
      busy={action.busy !== null}
      busyLabel="Creating…"
      commitLabel="Create station"
      commitDisabled={!ready}
      onClose={onClose}
      onCommit={() =>
        void action.run("create", async () => {
          await createStation(scope, {
            title: title.trim(),
            exam_code: examCode,
            content: parseJson(content),
            template_version_id: templateKey || null,
          });
          setTitle("");
          setContent("{}");
          setTemplateKey("");
          onCreated();
        })
      }
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label className="block text-osce-body font-semibold text-b2b-headline">
            Station title
          </label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className={`mt-1 ${getInputClassName()}`}
            placeholder="e.g. Chest pain counselling"
          />
        </div>
        <div>
          <label className="block text-osce-body font-semibold text-b2b-headline">Exam</label>
          <select
            value={examCode}
            onChange={(e) => setExamCode(e.target.value)}
            className="mt-1 w-full rounded-md border border-b2b-border bg-white px-3 py-2 text-osce-body text-b2b-headline"
          >
            <option value="">Select an exam…</option>
            {(exams.data?.items ?? []).map((exam) => (
              <option key={exam.id} value={exam.code}>
                {exam.name} ({exam.code})
              </option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label className="block text-osce-body font-semibold text-b2b-headline">Template</label>
        <select
          value={templateKey}
          onChange={(e) => setTemplateKey(e.target.value)}
          className="mt-1 w-full rounded-md border border-b2b-border bg-white px-3 py-2 text-osce-body text-b2b-headline"
        >
          <option value="">No template</option>
          {choices.map((choice) => (
            <option key={choice.id} value={choice.id}>
              {choice.label}
            </option>
          ))}
        </select>
        <p className="mt-1 text-osce-caption text-b2b-mid">
          Only published templates can be used for stations.
        </p>
      </div>

      <JsonField
        label="Content"
        hint="The fields the template asked for."
        value={content}
        onChange={setContent}
      />
    </AuthoringDialog>
  );
}
