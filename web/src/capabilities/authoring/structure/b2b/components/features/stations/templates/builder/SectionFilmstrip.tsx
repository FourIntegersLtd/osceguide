"use client";

import { useAssessWords } from "@/capabilities/assess-words";
import { useDroppable } from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { sectionDragId } from "@/capabilities/authoring/structure/b2b/lib/stations/structureBuilderOps";
import { audienceMeta, sectionAudience } from "@/capabilities/authoring/structure/b2b/lib/stations/blockRoles";
import type { TemplateKind } from "@/capabilities/authoring/structure/b2b/lib/stations/blockTypeLabels";
import type { StationSection } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { boardBtn, boardPad, boardButtonSmall } from "@/foundation/ui/boardKit";
import { builderUi } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/builderChrome";

function OutlineItem({
  kind,
  section,
  active,
  onFocus,
}: {
  kind: TemplateKind;
  section: StationSection;
  active: boolean;
  onFocus: () => void;
}) {
  const w = useAssessWords();
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: sectionDragId(section.id),
  });
  const { setNodeRef: setDropRef, isOver } = useDroppable({ id: `drop-section:${section.id}` });

  const fieldCount = section.blocks.length;
  const caption =
    kind === "station"
      ? audienceMeta(sectionAudience(section), w).label
      : fieldCount === 1
        ? "1 field"
        : `${fieldCount} fields`;

  return (
    <div ref={setNodeRef} style={{ transform: CSS.Transform.toString(transform), transition }}>
      <div
        ref={setDropRef}
        role="tab"
        aria-selected={active}
        tabIndex={active ? 0 : -1}
        onClick={onFocus}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onFocus();
          }
        }}
        className={[
          "flex cursor-pointer items-center gap-4 border-t border-osce-border-light p-2 text-assess-label text-ink",
          builderUi.focusRing,
          active ? "rounded-osce-md bg-assess-chip-info-bg" : "",
          isOver && !active ? "bg-osce-canvas" : "",
          isDragging ? "opacity-60" : "",
        ].join(" ")}
      >
        <button
          type="button"
          aria-label="Drag to reorder section"
          title="Drag to reorder"
          onClick={(e) => e.stopPropagation()}
          className={`cursor-grab active:cursor-grabbing ${builderUi.focusRing}`}
          {...attributes}
          {...listeners}
        >
          <span aria-hidden>⋮⋮</span>
        </button>
        <span className="min-w-0 flex-1">
          <span className="block truncate">{section.title || "Untitled section"}</span>
          <span className="block text-assess-meta text-ink-subtle">
            {caption}
            {fieldCount === 0 && isOver ? " · drop here" : ""}
          </span>
        </span>
      </div>
    </div>
  );
}

/** The board's sections card: a sortable, droppable list of the layout's sections and an add button. */
export function SectionOutline({
  kind,
  sections,
  activeSectionId,
  onFocusSection,
  onAddSection,
  readOnly = false,
}: {
  kind: TemplateKind;
  sections: StationSection[];
  activeSectionId: string | null;
  onFocusSection: (sectionId: string) => void;
  onAddSection: () => void;
  /** A published version: sections can be visited but not added. */
  readOnly?: boolean;
}) {
  return (
    <aside className={`${boardPad} !gap-1.5`} aria-label="Sections">
      <p className="text-assess-eyebrow uppercase text-ink-subtle">Sections</p>
      <div className="flex flex-col gap-1.5" role="tablist" aria-orientation="vertical">
        {sections.length === 0 ? (
          <p className="text-assess-meta text-ink-subtle">No sections yet.</p>
        ) : (
          <SortableContext items={sections.map((s) => sectionDragId(s.id))} strategy={verticalListSortingStrategy}>
            {sections.map((section) => (
              <OutlineItem
                key={section.id}
                kind={kind}
                section={section}
                active={section.id === activeSectionId}
                onFocus={() => onFocusSection(section.id)}
              />
            ))}
          </SortableContext>
        )}
      </div>
      <button type="button" className={boardButtonSmall} disabled={readOnly} onClick={onAddSection}>
        <span aria-hidden>+ </span>
        Add section
      </button>
    </aside>
  );
}

/** Below `lg` the outline gives way to this wrapping strip of section buttons (the board's sections card on a phone). */
export function SectionChipStrip({
  sections,
  activeSectionId,
  onFocusSection,
  onAddSection,
  readOnly = false,
}: {
  kind: TemplateKind;
  sections: StationSection[];
  activeSectionId: string | null;
  onFocusSection: (sectionId: string) => void;
  onAddSection: () => void;
  /** A published version: sections can be visited but not added. */
  readOnly?: boolean;
}) {
  return (
    <div className={`${boardPad} !gap-2 lg:hidden`} role="tablist" aria-label="Sections">
      <div className="flex flex-wrap items-center gap-2">
        {sections.map((section, index) => (
          <button
            key={section.id}
            type="button"
            role="tab"
            aria-selected={section.id === activeSectionId}
            onClick={() => onFocusSection(section.id)}
            className={`${boardBtn(section.id === activeSectionId ? "primary" : "default", true)} max-w-[15rem]`}
          >
            <span className="truncate">
              {index + 1}. {section.title || "Untitled section"}
            </span>
          </button>
        ))}
        <button type="button" className={boardButtonSmall} disabled={readOnly} onClick={onAddSection}>
          <span aria-hidden>+ </span>
          Section
        </button>
      </div>
    </div>
  );
}
