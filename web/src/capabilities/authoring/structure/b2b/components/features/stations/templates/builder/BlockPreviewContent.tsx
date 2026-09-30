import type { StationBlock } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { formsLabelForStationBlockType } from "@/capabilities/authoring/structure/b2b/lib/stations/blockTypeLabels";
import { RagGradePreviewRow } from "@/capabilities/authoring/structure/b2b/components/features/feedback/RagGradeControls";

/** WYSIWYG preview of a single block (ported from legacy StructureEditor Preview). */
export function BlockPreviewContent({
  block,
  showLabel = true,
  minimal = false,
}: {
  block: StationBlock;
  showLabel?: boolean;
  minimal?: boolean;
}) {
  const fieldClass = minimal
    ? "w-full rounded-lg border-0 bg-osce-canvas px-3 py-2 text-osce-meta text-osce-ink-500"
    : "w-full rounded-md border border-osce-border bg-osce-surface px-3 py-2 text-osce-body text-osce-ink-700";
  const chipClass = minimal
    ? "rounded-md bg-osce-canvas px-2 py-1 text-osce-caption text-osce-ink-500"
    : "rounded-full border border-osce-border bg-osce-surface px-2 py-1 text-osce-caption font-semibold text-osce-ink-700";

  return (
    <>
      {showLabel ? (
        <div className="flex items-center justify-between gap-3">
          <p className="truncate text-osce-body font-semibold text-osce-ink-700">
            {block.label}
          </p>
          <span className="shrink-0 text-osce-caption font-semibold text-osce-ink-500">
            {formsLabelForStationBlockType(block.type)}
          </span>
        </div>
      ) : null}
      {block.required && (
        <span
          className={
            minimal
              ? "mt-1 inline-block text-osce-caption font-medium text-osce-ink-500"
              : "mt-1 inline-block rounded-full border border-osce-warning-border bg-osce-warning-bg px-2 py-0.5 text-osce-caption font-semibold text-osce-warning-text"
          }
        >
          Required
        </span>
      )}
      <div className={showLabel ? "mt-2" : ""}>
        {block.type === "shortText" && (
          <input
            disabled
            placeholder={block.placeholder || block.label || "Short text"}
            className={fieldClass}
          />
        )}
        {block.type === "longText" && (
          <textarea
            disabled
            placeholder={block.placeholder || block.label || "Long text"}
            className={fieldClass}
            rows={2}
          />
        )}
        {block.type === "list" && (
          <div className={fieldClass}>
            {block.placeholder || block.label || "Add multiple items…"}
          </div>
        )}
        {block.type === "singleSelect" && (
          <div className="space-y-2">
            <select
              disabled
              className={`${fieldClass} max-w-md text-osce-ink-700`}
              value={block.options[0] ?? ""}
            >
              {(block.options.length ? block.options : ["Option 1"]).map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
            <div className="flex flex-wrap gap-1.5">
              {block.options.slice(0, 4).map((o) => (
                <span key={o} className={chipClass}>
                  {o}
                </span>
              ))}
            </div>
          </div>
        )}
        {block.type === "multiSelect" && (
          <div className="flex flex-wrap gap-1.5">
            {block.options.slice(0, 4).map((o) => (
              <span key={o} className={chipClass}>
                {o}
              </span>
            ))}
          </div>
        )}
        {block.type === "checklist" && (
          <div className="space-y-1">
            {block.items.slice(0, 5).map((it) => (
              <div
                key={it.id}
                className={`flex items-center gap-2 ${minimal ? "text-osce-meta text-osce-ink-500" : "text-osce-body text-osce-ink-700"}`}
              >
                <input
                  type="checkbox"
                  disabled
                  className="rounded border-osce-border"
                />
                <span>{it.label}</span>
              </div>
            ))}
          </div>
        )}
        {block.type === "scale" && (
          <div className="flex flex-wrap items-center gap-1.5">
            {Array.from({ length: block.max - block.min + 1 }, (_, i) => block.min + i)
              .slice(0, 8)
              .map((n) => (
                <span
                  key={n}
                  className={
                    minimal
                      ? "inline-flex h-7 min-w-[1.75rem] items-center justify-center rounded-md bg-osce-canvas text-osce-caption text-osce-ink-500"
                      : "inline-flex h-8 min-w-[2rem] items-center justify-center rounded-full border border-osce-border bg-osce-surface text-osce-body font-semibold text-osce-ink-700"
                  }
                >
                  {n}
                </span>
              ))}
          </div>
        )}
        {block.type === "media" && (
          <div className="flex gap-2">
            {[0, 1, 2].map((index) => (
              <span key={index} className={`h-12 w-16 rounded-md ${minimal ? "bg-osce-canvas" : "border border-osce-border bg-osce-canvas"}`} />
            ))}
          </div>
        )}
        {block.type === "records" && (
          <div className={`${fieldClass} flex flex-wrap gap-x-4 gap-y-1`}>
            {(block.fields?.length ? block.fields : [{ key: "details", label: "Details" }]).map((field) => (
              <span key={field.key}>{field.label}</span>
            ))}
          </div>
        )}
        {block.type === "qaList" && (
          <div className={fieldClass}>
            <p>1. Question</p>
            <p className="pl-4 opacity-80">Model answer</p>
          </div>
        )}
        {block.type === "groupedList" && (
          <div className={fieldClass}>
            <p className="font-semibold">Group</p>
            <p className="pl-4">1. Item, with reasons</p>
          </div>
        )}
        {block.type === "ragCriterion" && (
          <RagGradePreviewRow />
        )}
      </div>
    </>
  );
}
