"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { formsMetaForStationBlockType, type TemplateKind } from "@/capabilities/authoring/structure/b2b/lib/stations/blockTypeLabels";
import { blockRole, roleMeta } from "@/capabilities/authoring/structure/b2b/lib/stations/blockRoles";
import { blockDragId } from "@/capabilities/authoring/structure/b2b/lib/stations/structureBuilderOps";
import type {
  StationBlock,
  StationSection,
} from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import {
  builderUi,
  TypeBadge,
} from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/builderChrome";
import { HiChevronRight, HiOutlineEllipsisVertical } from "react-icons/hi2";

export function CanvasBlock({
  kind,
  section,
  block,
  selected,
  isDropBefore,
  onSelect,
}: {
  kind: TemplateKind;
  section: StationSection;
  block: StationBlock;
  selected: boolean;
  isDropBefore: boolean;
  onSelect: () => void;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: blockDragId(section.id, block.id) });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const meta = formsMetaForStationBlockType(block.type);
  const TypeIcon = meta.icon;
  const role = kind === "station" ? roleMeta(blockRole(block, section)) : null;
  const caption = role ? `${meta.formsLabel} · ${role.label}` : meta.formsLabel;

  return (
    <div ref={setNodeRef} style={style} className="relative">
      {isDropBefore && (
        <div className="absolute -top-px left-4 right-4 z-10 h-0.5 rounded-full bg-osce-accent" />
      )}
      <div
        role="button"
        tabIndex={0}
        aria-pressed={selected}
        className={[
          "group/row flex min-h-[3.25rem] cursor-pointer items-center gap-3 px-3 py-2.5 transition-colors",
          builderUi.focusRing,
          selected ? builderUi.selectedRow : builderUi.hoverRow,
          isDragging ? "opacity-50" : "",
        ].join(" ")}
        onClick={(e) => {
          e.stopPropagation();
          onSelect();
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onSelect();
          }
        }}
      >
        <button
          type="button"
          aria-label="Drag to reorder field"
          title="Drag to reorder"
          onClick={(e) => e.stopPropagation()}
          className={`-ml-1 inline-flex h-7 w-5 shrink-0 cursor-grab items-center justify-center rounded-osce-md text-ink-subtle opacity-0 transition-opacity hover:text-ink-muted active:cursor-grabbing group-hover/row:opacity-100 focus-visible:opacity-100 ${builderUi.focusRing}`}
          {...attributes}
          {...listeners}
        >
          <HiOutlineEllipsisVertical className="h-4 w-4" aria-hidden />
        </button>
        <TypeBadge className={selected ? "bg-osce-surface text-osce-accent" : ""}>
          <TypeIcon aria-hidden />
        </TypeBadge>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-osce-body font-medium text-ink-muted">
            {block.label || (
              <span className="font-normal italic text-ink-subtle">
                Untitled field
              </span>
            )}
            {block.required ? (
              <span
                className="ml-1 text-osce-danger-text"
                aria-label="Required"
                title="Required"
              >
                *
              </span>
            ) : null}
          </span>
          <span className="block truncate text-osce-caption text-ink-subtle">
            {caption}
          </span>
        </span>
        <HiChevronRight
          className={`h-4 w-4 shrink-0 transition-colors ${
            selected ? "text-osce-accent" : "text-ink-subtle/60 group-hover/row:text-ink-subtle"
          }`}
          aria-hidden
        />
      </div>
    </div>
  );
}
