"use client";

import { useId } from "react";
import { Checkbox, Select, Textarea } from "@/foundation/ui";
import type { MediaUploads } from "@/capabilities/authoring/structure/b2b/components/features/stations/pages/MediaBlockEditor";
import { RichBlockEditor } from "@/capabilities/authoring/structure/b2b/components/features/stations/pages/RichBlockEditors";
import { StationInstanceArrayField } from "@/capabilities/authoring/structure/b2b/components/features/stations/pages/StationInstanceArrayField";
import { splitMultilineToTrimmedLines } from "@/capabilities/authoring/structure/b2b/lib/string/splitMultilineToTrimmedLines";
import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";

type Block = StationStructure["sections"][number]["blocks"][number];

export function StationInstanceBlocks({
  blocks,
  content,
  onChange,
  readOnly,
  showBlockIds = false,
  listEditor = "admin",
  media,
}: {
  blocks: Block[];
  content: Record<string, unknown>;
  onChange: (next: Record<string, unknown>) => void;
  readOnly?: boolean;
  showBlockIds?: boolean;
  /** `admin` = B2C update-station list UI; `lines` = one textarea per line */
  listEditor?: "admin" | "lines";
  /** Upload and remove for media blocks, once the station has a saved version. */
  media?: MediaUploads;
}) {
  const ro = !!readOnly;
  const scope = useId();
  /** The id a block's control carries, so its label names it. */
  const controlId = (blockId: string) => `${scope}-${blockId}`;
  /** A group of buttons has no single control to point at; the group is named by its label. */
  const groupProps = (blockId: string) =>
    ({ role: "group", "aria-labelledby": `${controlId(blockId)}-label` }) as const;

  function patch(key: string, value: unknown) {
    onChange({ ...content, [key]: value });
  }

  function fieldLabel(label: string, required: boolean, blockId: string, grouped = false) {
    const text = (
      <>
        {label}
        {required ? <span className="text-osce-danger-text"> *</span> : null}
      </>
    );
    return (
      <div className="flex items-center justify-between gap-3">
        {grouped ? (
          <p id={`${controlId(blockId)}-label`} className="block text-osce-body font-medium text-ink">
            {text}
          </p>
        ) : (
          <label htmlFor={controlId(blockId)} className="block text-osce-body font-medium text-ink">
            {text}
          </label>
        )}
        {showBlockIds ? (
          <span className="text-osce-caption font-semibold text-ink-muted">ID: {blockId}</span>
        ) : null}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 md:items-start">
      {blocks.map((b) => {
        const key = b.id;
        const label = b.label;
        const required = !!(b as { required?: boolean }).required;

        if (b.type === "media" || b.type === "records" || b.type === "qaList" || b.type === "groupedList") {
          return (
            <RichBlockEditor
              key={b.id}
              block={b}
              value={content[key]}
              required={required}
              readOnly={ro}
              media={media}
              onChange={(next) => patch(key, next)}
            />
          );
        }
        if (b.type === "shortText") {
          return (
            <div key={b.id} className="min-w-0">
              {fieldLabel(label, required, key)}
              <input
                id={controlId(key)}
                readOnly={ro}
                disabled={ro}
                value={typeof content[key] === "string" ? content[key] : ""}
                onChange={(e) => patch(key, e.target.value)}
                className="mt-1 read-only:bg-surface-raised/60 disabled:opacity-90"
              />
            </div>
          );
        }
        if (b.type === "longText") {
          return (
            <div key={b.id} className="min-w-0 md:col-span-2">
              {fieldLabel(label, required, key)}
              <Textarea
                id={controlId(key)}
                readOnly={ro}
                disabled={ro}
                value={typeof content[key] === "string" ? content[key] : ""}
                onChange={(e) => patch(key, e.target.value)}
                className="mt-1 read-only:bg-surface-raised/60 disabled:opacity-90"
                rows={4}
              />
            </div>
          );
        }
        if (b.type === "list") {
          const items = Array.isArray(content[key])
            ? (content[key] as string[]).filter((x) => typeof x === "string")
            : [];
          if (listEditor === "admin") {
            return (
              <StationInstanceArrayField
                key={b.id}
                label={label}
                required={required}
                items={items}
                readOnly={ro}
                onChange={(next) => patch(key, next)}
              />
            );
          }
          return (
            <div key={b.id} className="min-w-0 md:col-span-2">
              {fieldLabel(label, required, key)}
              <Textarea
                id={controlId(key)}
                readOnly={ro}
                disabled={ro}
                value={items.join("\n")}
                onChange={(e) => patch(key, splitMultilineToTrimmedLines(e.target.value))}
                className="mt-1 read-only:bg-surface-raised/60 disabled:opacity-90"
                rows={4}
              />
              <p className="mt-1 text-osce-caption text-ink-muted">One item per line.</p>
            </div>
          );
        }
        if (b.type === "singleSelect") {
          const opts = (b as { options?: string[] }).options || [];
          return (
            <div key={b.id} className="min-w-0">
              {fieldLabel(label, required, key)}
              <Select
                id={controlId(key)}
                disabled={ro}
                value={typeof content[key] === "string" ? content[key] : ""}
                onChange={(e) => patch(key, e.target.value)}
                className="mt-1"
              >
                <option value="">Select…</option>
                {opts.map((o: string) => (
                  <option key={o} value={o}>{o}</option>
                ))}
              </Select>
            </div>
          );
        }
        if (b.type === "multiSelect") {
          const opts = (b as { options?: string[] }).options || [];
          const selected: string[] = Array.isArray(content[key]) ? (content[key] as string[]) : [];
          return (
            <div key={b.id} className="min-w-0 md:col-span-2">
              {fieldLabel(label, required, key, true)}
              <div className="mt-2 flex flex-wrap gap-2" {...groupProps(key)}>
                {opts.map((o: string) => {
                  const on = selected.includes(o);
                  return (
                    <button
                      key={o}
                      type="button"
                      disabled={ro}
                      onClick={() =>
                        patch(key, on ? selected.filter((x) => x !== o) : [...selected, o])
                      }
                      className={[
                        "rounded-osce-md border px-3 py-1.5 text-osce-caption font-semibold",
                        on
                          ? "border-accent bg-surface-raised text-accent"
                          : "border-border bg-white text-ink-muted hover:bg-surface-raised",
                        ro ? "cursor-default opacity-90" : "",
                      ].join(" ")}
                    >
                      {o}
                    </button>
                  );
                })}
              </div>
            </div>
          );
        }
        if (b.type === "checklist") {
          const checklistItems =
            (b as { items?: Array<{ id: string; label: string }> }).items || [];
          const selected: string[] = Array.isArray(content[key]) ? (content[key] as string[]) : [];
          return (
            <div key={b.id} className="min-w-0 md:col-span-2">
              {fieldLabel(label, required, key, true)}
              <div className="mt-2 space-y-2" {...groupProps(key)}>
                {checklistItems.map((it) => (
                  <Checkbox
                    key={it.id}
                    label={it.label}
                    className="items-center"
                    disabled={ro}
                    checked={selected.includes(it.id)}
                    onChange={(e) =>
                      patch(
                        key,
                        e.target.checked
                          ? [...selected, it.id]
                          : selected.filter((x) => x !== it.id),
                      )
                    }
                  />
                ))}
              </div>
            </div>
          );
        }
        if (b.type === "scale") {
          const min = (b as { min?: number }).min ?? 1;
          const max = (b as { max?: number }).max ?? 5;
          const val = typeof content[key] === "number" ? content[key] : null;
          return (
            <div key={b.id} className="min-w-0">
              {fieldLabel(label, required, key, true)}
              <div className="mt-2 flex flex-wrap gap-2" {...groupProps(key)}>
                {Array.from({ length: max - min + 1 }, (_, i) => min + i).map((n) => (
                  <button
                    key={n}
                    type="button"
                    disabled={ro}
                    onClick={() => patch(key, n)}
                    className={[
                      "inline-flex h-9 w-9 items-center justify-center rounded-full border text-osce-body font-semibold",
                      val === n
                        ? "border-accent bg-surface-raised text-accent"
                        : "border-border bg-white text-ink-muted hover:bg-surface-raised",
                      ro ? "cursor-default" : "",
                    ].join(" ")}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>
          );
        }
        return null;
      })}
    </div>
  );
}
