"use client";

import { Fragment } from "react";
import { useDroppable } from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import {
  AddFieldButton,
  InsertFieldBetween,
} from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/AddFieldMenu";
import { CanvasBlock } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/CanvasBlock";
import type { BuilderSelection } from "@/capabilities/authoring/structure/b2b/lib/stations/structureBuilderOps";
import { blockDragId } from "@/capabilities/authoring/structure/b2b/lib/stations/structureBuilderOps";
import { audienceMeta, sectionAudience } from "@/capabilities/authoring/structure/b2b/lib/stations/blockRoles";
import type { TemplateKind } from "@/capabilities/authoring/structure/b2b/lib/stations/blockTypeLabels";
import type {
  StationBlockType,
  StationSection,
} from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import {
  HiChevronLeft,
  HiChevronRight,
  HiOutlineCog6Tooth,
  HiOutlineRectangleStack,
  HiOutlineSquares2X2,
} from "react-icons/hi2";
import {
  BuilderButton,
  BuilderIconButton,
  builderUi,
  ToneBadge,
  toneClass,
  toneForAudience,
  toneForIndex,
  type BuilderTone,
} from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/builderChrome";

export function sectionTone(
  kind: TemplateKind,
  section: StationSection,
  index: number,
): BuilderTone {
  return kind === "station" ? toneForAudience[sectionAudience(section)] : toneForIndex(index);
}

export function SectionStage({
  kind,
  section,
  sectionIndex,
  sections,
  selection,
  dropTarget,
  onSelectNone,
  onSelectBlock,
  onSectionTitleChange,
  onSectionDescriptionChange,
  onOpenSectionSettings,
  onAddSection,
  onAddField,
  onOpenFieldTypesInfo,
  onStepSection,
}: {
  kind: TemplateKind;
  section: StationSection | null;
  sectionIndex: number;
  sections: StationSection[];
  selection: BuilderSelection;
  dropTarget: { sectionId: string; index: number } | null;
  onSelectNone: () => void;
  onSelectBlock: (sectionId: string, blockId: string) => void;
  onSectionTitleChange: (sectionId: string, title: string) => void;
  onSectionDescriptionChange: (sectionId: string, description: string) => void;
  onOpenSectionSettings: (sectionId: string) => void;
  onAddSection: () => void;
  onAddField: (type: StationBlockType, sectionId: string, index?: number) => void;
  onOpenFieldTypesInfo: () => void;
  onStepSection: (delta: -1 | 1) => void;
}) {
  const { setNodeRef: setDropRef, isOver } = useDroppable({
    id: section ? `drop-section:${section.id}` : "drop-sections-end",
    disabled: !section,
  });
  const sectionCount = sections.length;

  if (!section) {
    return (
      <main className={`min-h-0 min-w-0 flex-1 ${builderUi.canvas}`}>
        <div className="flex min-h-[360px] flex-col items-center justify-center px-6 py-16 text-center">
          <ToneBadge tone="primary" size="lg">
            <HiOutlineSquares2X2 aria-hidden />
          </ToneBadge>
          <p className="mt-4 text-osce-subheading font-semibold text-ink-muted">
            Start with a section
          </p>
          <p className="mt-1.5 max-w-sm text-osce-body text-ink-muted">
            {kind === "station"
              ? "A section is written for the patient, the candidate or the examiner. Add one, then add the fields it needs."
              : "Sections group related fields. Add one, then add the fields it needs one at a time."}
          </p>
          <BuilderButton variant="commit" className="mt-6" onClick={onAddSection}>
            Add your first section
          </BuilderButton>
        </div>
      </main>
    );
  }

  const tone = sectionTone(kind, section, sectionIndex);
  const audience = kind === "station" ? audienceMeta(sectionAudience(section)) : null;
  const HeaderIcon = audience ? audience.icon : HiOutlineRectangleStack;
  const sectionSelected =
    selection.kind === "section" && selection.sectionId === section.id;
  const hasPrev = sectionIndex > 0;
  const hasNext = sectionIndex < sectionCount - 1;
  const count = section.blocks.length;

  return (
    // Clicking empty canvas deselects, a pointer shortcut; the inspector's
    // close button and Escape are the keyboard way.
    // eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-noninteractive-element-interactions
    <main
      className={`min-h-0 min-w-0 flex-1 ${builderUi.canvas}`}
      onClick={onSelectNone}
    >
      {/* keyed so a section change re-runs the enter animation */}
      <div
        key={section.id}
        className="osce-builder-in mx-auto w-full max-w-[760px] px-4 py-6 sm:px-6 sm:py-8"
      >
        <header
          className={[
            "flex items-start gap-4 rounded-2xl px-5 py-5 ring-1 ring-inset transition-colors",
            toneClass[tone].band,
            sectionSelected ? toneClass[tone].ring : "ring-transparent",
          ].join(" ")}
        >
          <ToneBadge tone={tone} size="lg" className="bg-osce-surface/80 shadow-sm">
            <HeaderIcon aria-hidden />
          </ToneBadge>
          <div className="min-w-0 flex-1">
            <p className={`${builderUi.eyebrow} ${toneClass[tone].text}`}>
              {audience ? audience.label : `Section ${sectionIndex + 1}`}
              <span className="mx-1.5 opacity-50">·</span>
              {sectionIndex + 1} of {sectionCount}
              <span className="mx-1.5 opacity-50">·</span>
              {count === 1 ? "1 field" : `${count} fields`}
            </p>
            <input
              value={section.title}
              onChange={(e) => onSectionTitleChange(section.id, e.target.value)}
              onClick={(e) => e.stopPropagation()}
              className="mt-1 w-full border-0 bg-transparent p-0 text-osce-subheading font-semibold text-ink outline-none placeholder:text-ink-subtle"
              placeholder="Section title"
              aria-label="Section title"
            />
            <input
              value={section.description ?? ""}
              onChange={(e) =>
                onSectionDescriptionChange(section.id, e.target.value)
              }
              onClick={(e) => e.stopPropagation()}
              className="mt-1 w-full border-0 bg-transparent p-0 text-osce-body text-ink-muted outline-none placeholder:text-ink-subtle/80"
              placeholder="Add a short description (optional)"
              aria-label="Section description"
            />
          </div>
          <BuilderIconButton
            label="Section settings"
            className="bg-osce-surface/70 hover:bg-osce-surface"
            onClick={(e) => {
              e.stopPropagation();
              onOpenSectionSettings(section.id);
            }}
          >
            <HiOutlineCog6Tooth aria-hidden />
          </BuilderIconButton>
        </header>

        <section
          ref={setDropRef}
          aria-label="Fields"
          className={[
            "mt-5 overflow-hidden rounded-2xl transition-colors",
            builderUi.box,
            isOver ? "bg-osce-accent-muted/40" : builderUi.surface,
          ].join(" ")}
        >
          {count === 0 ? (
            <p className="px-5 py-8 text-center text-osce-body text-ink-subtle">
              No fields yet. Add the first one below.
            </p>
          ) : (
            <SortableContext
              items={section.blocks.map((b) => blockDragId(section.id, b.id))}
              strategy={verticalListSortingStrategy}
            >
              <div className={builderUi.divide}>
                {section.blocks.map((block, blockIndex) => (
                  <Fragment key={block.id}>
                    {blockIndex > 0 ? (
                      <InsertFieldBetween
                        kind={kind}
                        onPick={(type) => onAddField(type, section.id, blockIndex)}
                        onOpenFieldTypesInfo={onOpenFieldTypesInfo}
                      />
                    ) : null}
                    <CanvasBlock
                      kind={kind}
                      section={section}
                      block={block}
                      selected={
                        selection.kind === "block" &&
                        selection.blockId === block.id &&
                        selection.sectionId === section.id
                      }
                      isDropBefore={
                        dropTarget?.sectionId === section.id &&
                        dropTarget.index === blockIndex
                      }
                      onSelect={() => onSelectBlock(section.id, block.id)}
                    />
                  </Fragment>
                ))}
              </div>
            </SortableContext>
          )}
          {dropTarget?.sectionId === section.id && dropTarget.index >= count ? (
            <div className="mx-4 h-0.5 rounded-full bg-osce-accent" />
          ) : null}
          <div className={`p-3 ${count ? builderUi.t : ""}`}>
            <AddFieldButton
              kind={kind}
              onPick={(type) => onAddField(type, section.id)}
              onOpenFieldTypesInfo={onOpenFieldTypesInfo}
            />
          </div>
        </section>

        {sectionCount > 1 ? (
          <nav
            aria-label="Section navigation"
            className="mt-6 flex items-center justify-between gap-3"
          >
            <BuilderButton
              variant="ghost"
              disabled={!hasPrev}
              onClick={(e) => {
                e.stopPropagation();
                onStepSection(-1);
              }}
            >
              <HiChevronLeft className="h-4 w-4" aria-hidden />
              Previous
            </BuilderButton>
            <div className="flex items-center gap-1.5" aria-hidden>
              {sections.map((s, i) => (
                <span
                  key={s.id}
                  className={`h-1.5 rounded-full transition-all ${
                    i === sectionIndex ? "w-5" : "w-1.5 opacity-40"
                  } ${toneClass[sectionTone(kind, s, i)].dot}`}
                />
              ))}
            </div>
            <BuilderButton
              variant={hasNext ? "secondary" : "ghost"}
              disabled={!hasNext}
              onClick={(e) => {
                e.stopPropagation();
                onStepSection(1);
              }}
            >
              Next section
              <HiChevronRight className="h-4 w-4" aria-hidden />
            </BuilderButton>
          </nav>
        ) : null}
      </div>
    </main>
  );
}
