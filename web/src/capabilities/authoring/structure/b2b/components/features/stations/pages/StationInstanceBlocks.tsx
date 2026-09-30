"use client";

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

  function patch(key: string, value: unknown) {
    onChange({ ...content, [key]: value });
  }

  function fieldLabel(label: string, required: boolean, blockId: string) {
    return (
      <div className="flex items-center justify-between gap-3">
        <label className="block text-osce-body font-medium text-b2b-headline">
          {label}
          {required ? <span className="text-b2b-danger-text"> *</span> : null}
        </label>
        {showBlockIds ? (
          <span className="text-osce-caption font-semibold text-b2b-mid">ID: {blockId}</span>
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
                readOnly={ro}
                disabled={ro}
                value={typeof content[key] === "string" ? content[key] : ""}
                onChange={(e) => patch(key, e.target.value)}
                className="mt-1 w-full rounded-md border border-b2b-border bg-white px-3 py-2 text-osce-body text-b2b-headline read-only:bg-b2b-cream/60 disabled:opacity-90"
              />
            </div>
          );
        }
        if (b.type === "longText") {
          return (
            <div key={b.id} className="min-w-0 md:col-span-2">
              {fieldLabel(label, required, key)}
              <textarea
                readOnly={ro}
                disabled={ro}
                value={typeof content[key] === "string" ? content[key] : ""}
                onChange={(e) => patch(key, e.target.value)}
                className="mt-1 w-full rounded-md border border-b2b-border bg-white px-3 py-2 text-osce-body text-b2b-headline read-only:bg-b2b-cream/60 disabled:opacity-90"
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
              <textarea
                readOnly={ro}
                disabled={ro}
                value={items.join("\n")}
                onChange={(e) => patch(key, splitMultilineToTrimmedLines(e.target.value))}
                className="mt-1 w-full rounded-md border border-b2b-border bg-white px-3 py-2 text-osce-body text-b2b-headline read-only:bg-b2b-cream/60 disabled:opacity-90"
                rows={4}
              />
              <p className="mt-1 text-osce-caption text-b2b-mid">One item per line.</p>
            </div>
          );
        }
        if (b.type === "singleSelect") {
          const opts = (b as { options?: string[] }).options || [];
          return (
            <div key={b.id} className="min-w-0">
              {fieldLabel(label, required, key)}
              <select
                disabled={ro}
                value={typeof content[key] === "string" ? content[key] : ""}
                onChange={(e) => patch(key, e.target.value)}
                className="mt-1 w-full rounded-md border border-b2b-border bg-white px-3 py-2 text-osce-body text-b2b-headline disabled:bg-b2b-cream/60"
              >
                <option value="">Select…</option>
                {opts.map((o: string) => (
                  <option key={o} value={o}>{o}</option>
                ))}
              </select>
            </div>
          );
        }
        if (b.type === "multiSelect") {
          const opts = (b as { options?: string[] }).options || [];
          const selected: string[] = Array.isArray(content[key]) ? (content[key] as string[]) : [];
          return (
            <div key={b.id} className="min-w-0 md:col-span-2">
              {fieldLabel(label, required, key)}
              <div className="mt-2 flex flex-wrap gap-2">
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
                        "rounded-md border px-3 py-1.5 text-osce-caption font-semibold",
                        on
                          ? "border-b2b-accent bg-b2b-cream text-b2b-accent"
                          : "border-b2b-border bg-white text-b2b-graphite hover:bg-b2b-cream",
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
              {fieldLabel(label, required, key)}
              <div className="mt-2 space-y-2">
                {checklistItems.map((it) => (
                  <label
                    key={it.id}
                    className="flex items-center gap-2 text-osce-body text-b2b-headline"
                  >
                    <input
                      type="checkbox"
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
                    <span>{it.label}</span>
                  </label>
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
              {fieldLabel(label, required, key)}
              <div className="mt-2 flex flex-wrap gap-2">
                {Array.from({ length: max - min + 1 }, (_, i) => min + i).map((n) => (
                  <button
                    key={n}
                    type="button"
                    disabled={ro}
                    onClick={() => patch(key, n)}
                    className={[
                      "inline-flex h-9 w-9 items-center justify-center rounded-full border text-osce-body font-semibold",
                      val === n
                        ? "border-b2b-accent bg-b2b-cream text-b2b-accent"
                        : "border-b2b-border bg-white text-b2b-graphite hover:bg-b2b-cream",
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
