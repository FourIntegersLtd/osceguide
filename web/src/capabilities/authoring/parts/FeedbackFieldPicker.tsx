"use client";

import { Button, getInputClassName } from "@/foundation/ui";
import { AuthoringButton } from "@/capabilities/authoring/parts/AuthoringButton";
import { newStructureId } from "@/capabilities/authoring/parts/structureTypes";

export interface FeedbackFieldPath {
  id: string;
  path: string;
  label: string;
  included: boolean;
}

export interface FeedbackSelection {
  fields: FeedbackFieldPath[];
}

export function emptyFeedbackSelection(): FeedbackSelection {
  return { fields: [] };
}

export function feedbackSelectionFromJson(value: unknown): FeedbackSelection {
  if (!value || typeof value !== "object") return emptyFeedbackSelection();
  const record = value as { fields?: unknown };
  if (!Array.isArray(record.fields)) return emptyFeedbackSelection();
  const fields: FeedbackFieldPath[] = [];
  for (const entry of record.fields) {
    if (!entry || typeof entry !== "object") continue;
    const row = entry as Record<string, unknown>;
    const path = typeof row.path === "string" ? row.path : "";
    if (!path) continue;
    fields.push({
      id: typeof row.id === "string" ? row.id : newStructureId("fld"),
      path,
      label: typeof row.label === "string" ? row.label : path,
      included: row.included !== false,
    });
  }
  return { fields };
}

export function feedbackSelectionToJson(selection: FeedbackSelection): Record<string, unknown> {
  return {
    fields: selection.fields.map(({ path, label, included }) => ({
      path,
      label,
      included,
    })),
  };
}

export function FeedbackFieldPicker({
  value,
  onChange,
}: {
  value: FeedbackSelection;
  onChange: (next: FeedbackSelection) => void;
}) {
  const updateRow = (index: number, patch: Partial<FeedbackFieldPath>) => {
    const fields = value.fields.map((field, i) => (i === index ? { ...field, ...patch } : field));
    onChange({ fields });
  };

  return (
    <div className="flex flex-col gap-3">
      {value.fields.length === 0 ? (
        <p className="text-sm text-b2b-mid">No fields yet. Add paths the rubric exposes.</p>
      ) : null}
      <ul className="flex flex-col gap-2">
        {value.fields.map((field, index) => (
          <li
            key={field.id}
            className="flex flex-wrap items-center gap-2 rounded-md border border-b2b-border bg-white p-2"
          >
            <label className="flex items-center gap-2 text-sm text-b2b-headline">
              <input
                type="checkbox"
                checked={field.included}
                onChange={(e) => updateRow(index, { included: e.target.checked })}
              />
              Include
            </label>
            <input
              value={field.label}
              onChange={(e) => updateRow(index, { label: e.target.value })}
              className={`min-w-[8rem] flex-1 ${getInputClassName()}`}
              placeholder="Label"
            />
            <input
              value={field.path}
              onChange={(e) => updateRow(index, { path: e.target.value })}
              className={`min-w-[10rem] flex-1 ${getInputClassName()}`}
              placeholder="Rubric path"
            />
            <AuthoringButton
              variant="ghost"
              size="xs"
              onClick={() => onChange({ fields: value.fields.filter((_, i) => i !== index) })}
            >
              Remove
            </AuthoringButton>
          </li>
        ))}
      </ul>
      <AuthoringButton
        variant="secondary"
        size="sm"
        onClick={() =>
          onChange({
            fields: [
              ...value.fields,
              { id: newStructureId("fld"), path: "", label: "New field", included: true },
            ],
          })
        }
      >
        Add field
      </AuthoringButton>
    </div>
  );
}
