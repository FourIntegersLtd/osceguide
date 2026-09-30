"use client";

import { useState, type ReactNode } from "react";
import { HiOutlinePlus, HiOutlineXMark } from "react-icons/hi2";
import {
  MediaBlockEditor,
  type MediaUploads,
} from "@/capabilities/authoring/structure/b2b/components/features/stations/pages/MediaBlockEditor";
import {
  groupedItemsFromText,
  groupedItemsToText,
  isObject,
  type GroupedItem,
  type QaPair,
} from "@/capabilities/authoring/structure/b2b/lib/stations/richBlockValues";
import { splitMultilineToTrimmedLines } from "@/capabilities/authoring/structure/b2b/lib/string/splitMultilineToTrimmedLines";
import type { RecordField, StationBlock } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { b2bInputBase } from "@/capabilities/authoring/structure/b2b/theme/b2bUi";

type RichBlock = Extract<StationBlock, { type: "media" | "records" | "qaList" | "groupedList" }>;

const input = `${b2bInputBase} py-2 text-osce-body`;
const card = "rounded-md border border-b2b-border bg-b2b-cream/30 p-3";

function text(value: unknown): string {
  return typeof value === "string" ? value : value === undefined || value === null ? "" : String(value);
}

/** Editors for the rich block types, each writing the value shape the backend validates. */
export function RichBlockEditor({
  block,
  value,
  required,
  readOnly,
  media,
  onChange,
}: {
  block: RichBlock;
  value: unknown;
  required: boolean;
  readOnly: boolean;
  media?: MediaUploads;
  onChange: (next: unknown) => void;
}) {
  if (block.type === "media") {
    return (
      <MediaBlockEditor
        blockId={block.id}
        label={block.label}
        required={required}
        value={value}
        readOnly={readOnly}
        media={media}
        onChange={onChange}
      />
    );
  }

  return (
    <Field label={block.label} required={required}>
      {block.type === "records" ? (
        <RecordsEditor
          records={Array.isArray(value) ? value.filter(isObject) : []}
          fields={block.fields ?? []}
          readOnly={readOnly}
          onChange={onChange}
        />
      ) : block.type === "qaList" ? (
        <QaEditor
          pairs={(Array.isArray(value) ? value.filter(isObject) : []).map((pair) => ({
            question: text(pair.question),
            answer: text(pair.answer),
          }))}
          readOnly={readOnly}
          onChange={onChange}
        />
      ) : (
        <GroupsEditor groups={isObject(value) ? value : {}} readOnly={readOnly} onChange={onChange} />
      )}
    </Field>
  );
}

function Field({ label, required, children }: { label: string; required: boolean; children: ReactNode }) {
  return (
    <div className="min-w-0 space-y-2 md:col-span-2">
      <p className="text-osce-body font-medium text-b2b-headline">
        {label}
        {required ? <span className="text-b2b-danger-text"> *</span> : null}
      </p>
      {children}
    </div>
  );
}

function RowActions({ addLabel, onAdd, readOnly }: { addLabel: string; onAdd: () => void; readOnly: boolean }) {
  if (readOnly) return null;
  return (
    <button
      type="button"
      onClick={onAdd}
      className="inline-flex items-center gap-1 text-osce-caption font-semibold text-b2b-accent hover:underline"
    >
      <HiOutlinePlus className="h-4 w-4" aria-hidden />
      {addLabel}
    </button>
  );
}

function RemoveButton({ label, onRemove, readOnly }: { label: string; onRemove: () => void; readOnly: boolean }) {
  if (readOnly) return null;
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onRemove}
      className="shrink-0 rounded-md p-1 text-b2b-mid hover:bg-b2b-cream hover:text-b2b-danger-text"
    >
      <HiOutlineXMark className="h-4 w-4" aria-hidden />
    </button>
  );
}

/** One card per record, an input per template column; a list cell is edited one item per line. */
function RecordsEditor({
  records,
  fields,
  readOnly,
  onChange,
}: {
  records: Record<string, unknown>[];
  fields: RecordField[];
  readOnly: boolean;
  onChange: (next: Record<string, unknown>[]) => void;
}) {
  const columns = fields.length > 0 ? fields : [{ key: "details", label: "Details" }];
  const patch = (index: number, key: string, cell: unknown) =>
    onChange(records.map((record, at) => (at === index ? { ...record, [key]: cell } : record)));
  return (
    <div className="space-y-3">
      {records.map((record, index) => (
        <div key={index} className={card}>
          <div className="mb-2 flex items-center justify-between">
            <span className="text-osce-caption font-semibold text-b2b-mid">Record {index + 1}</span>
            <RemoveButton
              label={`Remove record ${index + 1}`}
              readOnly={readOnly}
              onRemove={() => onChange(records.filter((_, at) => at !== index))}
            />
          </div>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
            {columns.map(({ key, label }) => {
              const cell = record[key];
              return (
                <label key={key} className="block min-w-0 text-osce-caption font-medium text-b2b-mid">
                  {label}
                  {Array.isArray(cell) ? (
                    <textarea
                      readOnly={readOnly}
                      value={cell.map(text).join("\n")}
                      onChange={(event) => patch(index, key, splitMultilineToTrimmedLines(event.target.value))}
                      className={`${input} mt-1`}
                      rows={3}
                    />
                  ) : (
                    <input
                      readOnly={readOnly}
                      value={text(cell)}
                      onChange={(event) => patch(index, key, event.target.value)}
                      className={`${input} mt-1`}
                    />
                  )}
                </label>
              );
            })}
          </div>
        </div>
      ))}
      <RowActions addLabel="Add record" readOnly={readOnly} onAdd={() => onChange([...records, {}])} />
    </div>
  );
}

function QaEditor({
  pairs,
  readOnly,
  onChange,
}: {
  pairs: QaPair[];
  readOnly: boolean;
  onChange: (next: QaPair[]) => void;
}) {
  const patch = (index: number, change: Partial<QaPair>) =>
    onChange(pairs.map((pair, at) => (at === index ? { ...pair, ...change } : pair)));
  return (
    <div className="space-y-3">
      {pairs.map((pair, index) => (
        <div key={index} className={card}>
          <div className="flex items-start gap-2">
            <span className="pt-2 text-osce-body font-semibold text-b2b-mid">{index + 1}.</span>
            <div className="min-w-0 flex-1 space-y-2">
              <input
                readOnly={readOnly}
                aria-label={`Question ${index + 1}`}
                placeholder="Question"
                value={pair.question}
                onChange={(event) => patch(index, { question: event.target.value })}
                className={input}
              />
              <textarea
                readOnly={readOnly}
                aria-label={`Answer ${index + 1}`}
                placeholder="Model answer"
                value={pair.answer}
                onChange={(event) => patch(index, { answer: event.target.value })}
                className={input}
                rows={3}
              />
            </div>
            <RemoveButton
              label={`Remove question ${index + 1}`}
              readOnly={readOnly}
              onRemove={() => onChange(pairs.filter((_, at) => at !== index))}
            />
          </div>
        </div>
      ))}
      <RowActions
        addLabel="Add question"
        readOnly={readOnly}
        onAdd={() => onChange([...pairs, { question: "", answer: "" }])}
      />
    </div>
  );
}

/** A heading per group; its items typed one per line, "- " lines as reasons under the item above. */
function GroupsEditor({
  groups,
  readOnly,
  onChange,
}: {
  groups: Record<string, unknown>;
  readOnly: boolean;
  onChange: (next: Record<string, GroupedItem[]>) => void;
}) {
  const entries = Object.entries(groups).map(([name, items]) => [name, (Array.isArray(items) ? items : []) as GroupedItem[]] as const);
  const write = (next: (readonly [string, GroupedItem[]])[]) => onChange(Object.fromEntries(next));
  return (
    <div className="space-y-3">
      {entries.map(([name, items], index) => (
        <div key={index} className={card}>
          <div className="mb-2 flex items-center gap-2">
            <input
              readOnly={readOnly}
              aria-label={`Group ${index + 1} name`}
              value={name}
              onChange={(event) =>
                write(entries.map((entry, at) => (at === index ? [event.target.value, entry[1]] : entry)))
              }
              className={`${input} font-semibold`}
            />
            <RemoveButton
              label={`Remove group ${name}`}
              readOnly={readOnly}
              onRemove={() => write(entries.filter((_, at) => at !== index))}
            />
          </div>
          <GroupItemsText
            items={items}
            readOnly={readOnly}
            onChange={(next) => write(entries.map((entry, at) => (at === index ? [entry[0], next] : entry)))}
          />
        </div>
      ))}
      <p className="text-osce-caption text-b2b-mid">
        One item per line. Start a line with &quot;- &quot; to add a reason under the item above.
      </p>
      <RowActions
        addLabel="Add group"
        readOnly={readOnly}
        onAdd={() => write([...entries, [`Group ${entries.length + 1}`, []]])}
      />
    </div>
  );
}

/** Keeps the typed text locally, so a blank line being typed is not parsed away mid-edit. */
function GroupItemsText({
  items,
  readOnly,
  onChange,
}: {
  items: GroupedItem[];
  readOnly: boolean;
  onChange: (next: GroupedItem[]) => void;
}) {
  const [draft, setDraft] = useState(() => groupedItemsToText(items));
  return (
    <textarea
      readOnly={readOnly}
      value={draft}
      onChange={(event) => {
        setDraft(event.target.value);
        onChange(groupedItemsFromText(event.target.value));
      }}
      className={input}
      rows={5}
    />
  );
}
