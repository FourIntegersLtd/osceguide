"use client";

import { useId, type ReactNode } from "react";
import { cn, getInputClassName } from "@/foundation/ui";
import { useRubricBuilder } from "@/capabilities/authoring/rubrics/builderContext";
import {
  GroupHeading,
  ItemControls,
  NumberAtPath,
  ProblemNote,
  SelectAtPath,
  TextAtPath,
  ToggleAtPath,
} from "@/capabilities/authoring/rubrics/formParts";
import { getAt, isJsonObject, listAt, pathText, setAt, type JsonPath } from "@/capabilities/authoring/rubrics/jsonPath";
import { problemsAt, problemsWithin } from "@/capabilities/authoring/rubrics/problems";
import { appendAt, newField, readRating, withFieldType } from "@/capabilities/authoring/rubrics/rubricEdits";
import {
  FIELD_ROLES,
  FIELD_SOURCES,
  FIELD_TYPES,
  type FieldType,
} from "@/capabilities/authoring/rubrics/rubricVocabulary";

/**
 * A list of fields, and one field, at any depth.
 *
 * A field is what the marker writes: a grade, a comment, a pick-one, or a
 * group or repeating record of further fields. The same card edits a domain's
 * competency fields, a written section's fields and a group's children, so it
 * calls itself for a group's own list. A rating field is only offered where
 * the backend allows one: among a domain's competency fields.
 */

/** Every field in the list at `listPath`, with a picker that adds one of any type. */
export function FieldList({
  listPath,
  heading,
  allowRating = false,
  depth = 0,
}: {
  listPath: JsonPath;
  heading: string;
  allowRating?: boolean;
  depth?: number;
}) {
  const { structure, edit, problems, readOnly } = useRubricBuilder();
  const fields = listAt(structure, listPath);
  const ratingField = readRating(structure).field;
  const offered = FIELD_TYPES.filter((choice) => allowRating || choice.value !== "rating");
  return (
    <div className="space-y-2" data-path={pathText(listPath)}>
      <GroupHeading count={fields.length}>{heading}</GroupHeading>
      <ProblemNote messages={problemsAt(problems, listPath)} />
      {fields.map((_field, index) => (
        <FieldCard
          key={index}
          path={[...listPath, index]}
          allowRating={allowRating}
          depth={depth}
          controls={<ItemControls listPath={listPath} index={index} count={fields.length} noun="field" />}
        />
      ))}
      {readOnly ? null : (
        <AddFieldPicker
          types={offered.map((choice) => ({ value: choice.value, label: choice.label }))}
          onAdd={(type) => edit((current) => appendAt(current, listPath, newField(type, listAt(current, listPath), ratingField)))}
        />
      )}
    </div>
  );
}

function AddFieldPicker({ types, onAdd }: { types: { value: FieldType; label: string }[]; onAdd: (type: FieldType) => void }) {
  const pickerId = useId();
  return (
    <div className="flex items-center gap-2">
      <label htmlFor={pickerId} className="sr-only">
        Add a field
      </label>
      <select
        id={pickerId}
        value=""
        onChange={(event) => {
          if (event.target.value) onAdd(event.target.value as FieldType);
        }}
        className={cn(getInputClassName({ size: "sm" }), "w-auto border-dashed text-osce-ink-500")}
      >
        <option value="">+ Add a field…</option>
        {types.map((type) => (
          <option key={type.value} value={type.value}>
            {type.label}
          </option>
        ))}
      </select>
    </div>
  );
}

/** One field: what it is called, what kind of answer it takes, and who writes it. */
export function FieldCard({
  path,
  allowRating = false,
  depth = 0,
  controls,
}: {
  path: JsonPath;
  allowRating?: boolean;
  depth?: number;
  controls?: ReactNode;
}) {
  const { structure, edit, problems } = useRubricBuilder();
  const field = getAt(structure, path);
  if (!isJsonObject(field)) return null;
  const type = typeof field.type === "string" ? (field.type as FieldType) : "shortText";
  const ratingField = readRating(structure).field;
  const typeChoices = FIELD_TYPES.filter((choice) => allowRating || choice.value !== "rating" || type === "rating");
  const inside = problemsWithin(problems, path);
  return (
    <div
      data-path={pathText(path)}
      className={cn(
        "space-y-3 rounded-osce-md border bg-osce-surface p-3",
        inside > 0 ? "border-osce-danger/40" : "border-osce-border",
        depth > 0 && "bg-osce-canvas",
      )}
    >
      <div className="flex items-start gap-2">
        <div className="grid min-w-0 flex-1 gap-3 sm:grid-cols-3">
          <TextAtPath path={[...path, "label"]} label="Label" placeholder="What the reader sees" />
          <SelectAtPath
            path={[...path, "type"]}
            label="Answer"
            choices={typeChoices}
            onPick={(next) => edit((current) => setAt(current, path, withFieldType(field, next, ratingField)))}
          />
          <SelectAtPath path={[...path, "role"]} label="Role" choices={FIELD_ROLES} />
        </div>
        {controls}
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <TextAtPath path={[...path, "id"]} label="Id" mono hint={type === "rating" ? "Always the rating's field name." : undefined} />
        <SelectAtPath path={[...path, "source"]} label="Written by" choices={FIELD_SOURCES} emptyLabel="The marker" />
        {type === "list" || type === "records" ? (
          <NumberAtPath path={[...path, "minItems"]} label="At least" step="1" hint="Fewest entries the marker must give." />
        ) : (
          <div className="flex items-end pb-1">
            <ToggleAtPath path={[...path, "required"]} label="Required" defaultOn />
          </div>
        )}
      </div>
      <TextAtPath path={[...path, "instructions"]} label="Instructions to the marker" rows={2} placeholder="What to write here, and how." />
      {type === "singleSelect" ? <OptionsEditor path={[...path, "options"]} /> : null}
      {type === "group" || type === "records" ? (
        <div className="border-l-2 border-osce-border pl-3">
          <FieldList listPath={[...path, "fields"]} heading={type === "records" ? "Each entry holds" : "The group holds"} depth={depth + 1} />
        </div>
      ) : null}
    </div>
  );
}

/** A pick-one's options, one per line. Blank lines are dropped when the box loses focus. */
function OptionsEditor({ path }: { path: JsonPath }) {
  const { structure, edit, problems, readOnly } = useRubricBuilder();
  const inputId = useId();
  const options = listAt(structure, path).map(String);
  const messages = problemsAt(problems, path);
  return (
    <div>
      <label htmlFor={inputId} className="block text-osce-meta font-medium text-osce-ink-500">
        Options, one per line
      </label>
      <textarea
        id={inputId}
        data-path={pathText(path)}
        rows={Math.max(2, options.length)}
        readOnly={readOnly}
        value={options.join("\n")}
        onChange={(event) => {
          const lines = event.target.value.split("\n");
          edit((current) => setAt(current, path, lines));
        }}
        onBlur={() => edit((current) => setAt(current, path, listAt(current, path).map(String).filter((line) => line.trim() !== "")))}
        className={cn(getInputClassName({ size: "sm", invalid: messages.length > 0 }), "mt-1 py-2")}
      />
      <ProblemNote messages={messages} />
    </div>
  );
}
