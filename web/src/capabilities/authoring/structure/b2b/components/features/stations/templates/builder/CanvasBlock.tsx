"use client";

import { useAssessWords } from "@/capabilities/assess-words";
import type { ReactNode } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { formsMetaForStationBlockType, type TemplateKind } from "@/capabilities/authoring/structure/b2b/lib/stations/blockTypeLabels";
import { blockRole, roleMeta } from "@/capabilities/authoring/structure/b2b/lib/stations/blockRoles";
import { blockDragId } from "@/capabilities/authoring/structure/b2b/lib/stations/structureBuilderOps";
import type { StationBlock, StationSection } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { boardRow } from "@/foundation/ui/boardKit";
import { builderUi } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/builderChrome";

/** One field of the active section: the board's row, its name over "type · role · Required". */
export function CanvasBlock({
  kind,
  section,
  block,
  first,
  selected,
  isDropBefore,
  insertAbove,
  onSelect,
}: {
  kind: TemplateKind;
  section: StationSection;
  block: StationBlock;
  first: boolean;
  selected: boolean;
  isDropBefore: boolean;
  /** The hover "+" that inserts a field above this one. */
  insertAbove?: ReactNode;
  onSelect: () => void;
}) {
  const w = useAssessWords();
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: blockDragId(section.id, block.id),
  });

  const meta = formsMetaForStationBlockType(block.type);
  const role = kind === "station" ? roleMeta(blockRole(block, section), w) : null;
  const caption = [meta.formsLabel, role?.label, block.required ? "Required" : null].filter(Boolean).join(" · ");

  return (
    <div ref={setNodeRef} style={{ transform: CSS.Transform.toString(transform), transition }} className="relative">
      {isDropBefore && <div className="absolute -top-px left-4 right-4 z-10 h-0.5 rounded-full bg-osce-accent" />}
      {insertAbove ? <div className="absolute inset-x-0 -top-2.5 z-10">{insertAbove}</div> : null}
      <div
        role="button"
        tabIndex={0}
        aria-pressed={selected}
        className={[
          "group/row cursor-pointer",
          boardRow,
          first ? "!border-t-0" : "",
          builderUi.focusRing,
          selected ? "bg-assess-chip-info-bg" : "hover:bg-osce-canvas",
          isDragging ? "opacity-50" : "",
        ].join(" ")}
        onClick={onSelect}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onSelect();
          }
        }}
      >
        <span className="min-w-0 flex-1">
          <span className="block truncate">
            {block.label || <span className="italic text-ink-subtle">Untitled field</span>}
          </span>
          <span className="block truncate text-assess-meta text-ink-subtle">{caption}</span>
        </span>
        <button
          type="button"
          aria-label="Drag to reorder field"
          title="Drag to reorder"
          onClick={(e) => e.stopPropagation()}
          className={`cursor-grab text-ink-subtle opacity-0 active:cursor-grabbing group-hover/row:opacity-100 focus-visible:opacity-100 ${builderUi.focusRing}`}
          {...attributes}
          {...listeners}
        >
          <span aria-hidden>⋮⋮</span>
        </button>
      </div>
    </div>
  );
}
