"use client";

import { useDroppable } from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { sectionDragId } from "@/capabilities/authoring/structure/b2b/lib/stations/structureBuilderOps";
import { audienceMeta, sectionAudience, STATION_AUDIENCES } from "@/capabilities/authoring/structure/b2b/lib/stations/blockRoles";
import type { TemplateKind } from "@/capabilities/authoring/structure/b2b/lib/stations/blockTypeLabels";
import type { StationSection } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import {
  HiOutlineEllipsisVertical,
  HiOutlineRectangleStack,
  HiPlus,
} from "react-icons/hi2";
import {
  BuilderButton,
  builderUi,
  ToneBadge,
  toneClass,
  toneForAudience,
  toneForIndex,
} from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/builderChrome";

function OutlineItem({
  kind,
  section,
  index,
  active,
  onFocus,
}: {
  kind: TemplateKind;
  section: StationSection;
  index: number;
  active: boolean;
  onFocus: () => void;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: sectionDragId(section.id) });

  const { setNodeRef: setDropRef, isOver } = useDroppable({
    id: `drop-section:${section.id}`,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const fieldCount = section.blocks.length;
  const audience = kind === "station" ? audienceMeta(sectionAudience(section)) : null;
  const tone = audience ? toneForAudience[audience.id] : toneForIndex(index);
  const Icon = audience ? audience.icon : HiOutlineRectangleStack;

  return (
    <div ref={setNodeRef} style={style}>
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
          "group/item flex cursor-pointer items-center gap-2.5 rounded-xl py-2 pl-1.5 pr-2.5 transition-colors",
          builderUi.focusRing,
          active
            ? builderUi.selectedRow
            : "hover:bg-osce-surface hover:shadow-sm",
          isOver && !active ? "bg-osce-surface ring-1 ring-inset ring-osce-accent-subtle" : "",
          isDragging ? "opacity-60" : "",
        ].join(" ")}
      >
        <button
          type="button"
          aria-label="Drag to reorder section"
          title="Drag to reorder"
          onClick={(e) => e.stopPropagation()}
          className={`inline-flex h-7 w-4 shrink-0 cursor-grab items-center justify-center rounded-osce-md text-ink-subtle opacity-0 transition-opacity active:cursor-grabbing group-hover/item:opacity-100 focus-visible:opacity-100 ${builderUi.focusRing}`}
          {...attributes}
          {...listeners}
        >
          <HiOutlineEllipsisVertical className="h-4 w-4" aria-hidden />
        </button>
        <ToneBadge tone={tone} size="sm">
          <Icon aria-hidden />
        </ToneBadge>
        <span className="min-w-0 flex-1">
          <span
            className={[
              "block truncate text-osce-body",
              active ? "font-semibold text-ink" : "font-medium text-ink-muted",
            ].join(" ")}
          >
            {section.title || "Untitled section"}
          </span>
          <span className="block text-osce-caption text-ink-subtle">
            {fieldCount === 1 ? "1 field" : `${fieldCount} fields`}
            {fieldCount === 0 && isOver ? " · drop here" : ""}
          </span>
        </span>
        <span
          className={`h-1.5 w-1.5 shrink-0 rounded-full transition-opacity ${toneClass[tone].dot} ${
            active ? "opacity-100" : "opacity-0"
          }`}
          aria-hidden
        />
      </div>
    </div>
  );
}

/** Desktop outline (left column) — sortable, droppable section list. */
export function SectionOutline({
  kind,
  sections,
  activeSectionId,
  onFocusSection,
  onAddSection,
}: {
  kind: TemplateKind;
  sections: StationSection[];
  activeSectionId: string | null;
  onFocusSection: (sectionId: string) => void;
  onAddSection: () => void;
}) {
  return (
    <aside
      className={`hidden w-[248px] shrink-0 flex-col self-stretch lg:flex ${builderUi.canvas} ${builderUi.r}`}
      aria-label="Sections"
    >
      <div className="flex items-center justify-between px-4 pb-2 pt-4">
        <p className={builderUi.eyebrow}>Sections</p>
        <span className="rounded-full bg-osce-surface px-2 py-0.5 text-osce-micro font-semibold tabular-nums text-ink-muted ring-1 ring-inset ring-osce-border">
          {sections.length}
        </span>
      </div>
      <div
        className="min-h-0 flex-1 space-y-1 px-2"
        role="tablist"
        aria-orientation="vertical"
      >
        {sections.length === 0 ? (
          <p className="px-2 py-2 text-osce-caption text-ink-subtle">
            No sections yet.
          </p>
        ) : (
          <SortableContext
            items={sections.map((s) => sectionDragId(s.id))}
            strategy={verticalListSortingStrategy}
          >
            <div className="space-y-1">
              {sections.map((section, index) => (
                <OutlineItem
                  key={section.id}
                  kind={kind}
                  section={section}
                  index={index}
                  active={section.id === activeSectionId}
                  onFocus={() => onFocusSection(section.id)}
                />
              ))}
            </div>
          </SortableContext>
        )}
      </div>
      {kind === "station" ? (
        <div className="mx-3 mb-1 flex flex-wrap gap-x-3 gap-y-1 border-t border-osce-border-light pt-3">
          {STATION_AUDIENCES.map((a) => (
            <span key={a.id} className="inline-flex items-center gap-1.5 text-osce-micro text-ink-subtle">
              <span className={`h-2 w-2 rounded-full ${toneClass[toneForAudience[a.id]].dot}`} aria-hidden />
              {a.label}
            </span>
          ))}
        </div>
      ) : null}
      <div className="p-3">
        <BuilderButton
          variant="secondary"
          className="w-full border-dashed"
          onClick={onAddSection}
        >
          <HiPlus className="h-4 w-4" aria-hidden />
          Add section
        </BuilderButton>
      </div>
    </aside>
  );
}

/** Narrow-screen replacement for the outline: a wrapping chip strip. */
export function SectionChipStrip({
  kind,
  sections,
  activeSectionId,
  onFocusSection,
  onAddSection,
}: {
  kind: TemplateKind;
  sections: StationSection[];
  activeSectionId: string | null;
  onFocusSection: (sectionId: string) => void;
  onAddSection: () => void;
}) {
  return (
    <div
      className={`flex flex-wrap items-center gap-2 px-4 py-3 lg:hidden ${builderUi.canvas} ${builderUi.b}`}
      role="tablist"
      aria-label="Sections"
    >
      {sections.map((section, index) => {
        const active = section.id === activeSectionId;
        const tone =
          kind === "station" ? toneForAudience[sectionAudience(section)] : toneForIndex(index);
        return (
          <button
            key={section.id}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onFocusSection(section.id)}
            className={[
              "inline-flex max-w-[15rem] items-center gap-2 rounded-full py-1 pl-1 pr-3 text-osce-caption transition-colors",
              builderUi.focusRing,
              active
                ? `${toneClass[tone].badge} font-semibold ring-1 ring-inset ${toneClass[tone].ring}`
                : "bg-osce-surface font-medium text-ink-muted ring-1 ring-inset ring-osce-border hover:text-ink-muted",
            ].join(" ")}
          >
            <span
              className={`inline-flex h-5 w-5 items-center justify-center rounded-full text-osce-micro font-semibold tabular-nums ${
                active ? "bg-osce-surface/80" : toneClass[tone].badge
              }`}
            >
              {index + 1}
            </span>
            <span className="truncate">{section.title || "Untitled section"}</span>
          </button>
        );
      })}
      <button
        type="button"
        onClick={onAddSection}
        className={`inline-flex items-center gap-1 rounded-full border border-dashed border-osce-border px-3 py-1 text-osce-caption font-medium text-ink-muted hover:bg-osce-surface hover:text-ink-muted ${builderUi.focusRing}`}
      >
        <HiPlus className="h-3.5 w-3.5" aria-hidden />
        Section
      </button>
    </div>
  );
}

/** @deprecated Use {@link SectionOutline}; kept so existing imports compile. */
export const SectionFilmstrip = SectionOutline;
