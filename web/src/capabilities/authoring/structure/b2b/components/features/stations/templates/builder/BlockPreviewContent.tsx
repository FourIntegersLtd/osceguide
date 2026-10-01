import { Checkbox, Select, Textarea } from "@/foundation/ui";
import type { StationBlock } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { formsLabelForStationBlockType } from "@/capabilities/authoring/structure/b2b/lib/stations/blockTypeLabels";
import { RagGradePreviewRow } from "@/capabilities/authoring/structure/b2b/components/features/feedback/RagGradeControls";

/** Shows one block the way a candidate will see it. */
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
    ? "w-full rounded-osce-lg border-0 bg-osce-canvas px-3 py-2 text-osce-meta text-ink-muted"
    : "w-full rounded-osce-md border border-osce-border bg-osce-surface px-3 py-2 text-osce-body text-ink-muted";
  const chipClass = minimal
    ? "rounded-osce-md bg-osce-canvas px-2 py-1 text-osce-caption text-ink-muted"
    : "rounded-full border border-osce-border bg-osce-surface px-2 py-1 text-osce-caption font-semibold text-ink-muted";

  return (
    <>
      {showLabel ? (
        <div className="flex items-center justify-between gap-3">
          <p className="truncate text-osce-body font-semibold text-ink-muted">
            {block.label}
          </p>
          <span className="shrink-0 text-osce-caption font-semibold text-ink-muted">
            {formsLabelForStationBlockType(block.type)}
          </span>
        </div>
      ) : null}
      {block.required && (
        <span
          className={
            minimal
              ? "mt-1 inline-block text-osce-caption font-medium text-ink-muted"
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
          <Textarea
            disabled
            readOnly
            tabIndex={-1}
            placeholder={block.placeholder || block.label || "Long text"}
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
            <Select
              disabled
              tabIndex={-1}
              className="max-w-md"
              value={block.options[0] ?? ""}
            >
              {(block.options.length ? block.options : ["Option 1"]).map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </Select>
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
              <Checkbox
                key={it.id}
                disabled
                tabIndex={-1}
                label={it.label}
                className="items-center"
              />
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
                      ? "inline-flex h-7 min-w-[1.75rem] items-center justify-center rounded-osce-md bg-osce-canvas text-osce-caption text-ink-muted"
                      : "inline-flex h-8 min-w-[2rem] items-center justify-center rounded-full border border-osce-border bg-osce-surface text-osce-body font-semibold text-ink-muted"
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
              <span key={index} className={`h-12 w-16 rounded-osce-md ${minimal ? "bg-osce-canvas" : "border border-osce-border bg-osce-canvas"}`} />
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
