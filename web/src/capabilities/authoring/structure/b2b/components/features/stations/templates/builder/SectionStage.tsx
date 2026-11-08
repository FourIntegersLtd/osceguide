"use client";

import { useAssessWords } from "@/capabilities/assess-words";
import type { ReactNode } from "react";
import { useDroppable } from "@dnd-kit/core";
import {
  HiOutlineArrowUturnLeft,
  HiOutlineArrowUturnRight,
  HiOutlineChevronLeft,
  HiOutlineChevronRight,
  HiOutlineCog6Tooth,
} from "react-icons/hi2";
import { AnchoredTooltip } from "@/foundation/ui";
import { b2bIconTooltipChipBase } from "@/foundation/ui/b2bTokens";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import {
  AddFieldPanel,
  InsertFieldBetween,
} from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/AddFieldMenu";
import { CanvasBlock } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/CanvasBlock";
import type { BuilderSelection } from "@/capabilities/authoring/structure/b2b/lib/stations/structureBuilderOps";
import { blockDragId } from "@/capabilities/authoring/structure/b2b/lib/stations/structureBuilderOps";
import type { TemplateKind } from "@/capabilities/authoring/structure/b2b/lib/stations/blockTypeLabels";
import type { StationBlockType, StationSection } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { boardBtn, boardCard, boardCardClipped, boardInput, boardPad, boardButtonSmall } from "@/foundation/ui/boardKit";

/** A square icon button whose name shows in a tooltip on hover and focus. */
function IconTool({ label, disabled, onClick, children }: { label: string; disabled?: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <AnchoredTooltip label={label} placement="bottom" chipClassName={b2bIconTooltipChipBase}>
      <button
        type="button"
        aria-label={label}
        disabled={disabled}
        onClick={onClick}
        className="inline-flex h-9 w-9 items-center justify-center rounded-osce-md border border-osce-border bg-osce-surface text-ink hover:bg-surface-raised disabled:pointer-events-none disabled:opacity-40"
      >
        {children}
      </button>
    </AnchoredTooltip>
  );
}

/** The board's section card: the section's name and description, its fields in a list, and the add-field fold. */
export function SectionStage({
  kind,
  readOnly = false,
  section,
  selection,
  dropTarget,
  sectionIndex,
  sectionCount,
  onStepSection,
  canUndo,
  canRedo,
  onUndo,
  onRedo,
  onSelectBlock,
  onSectionTitleChange,
  onSectionDescriptionChange,
  onOpenSectionSettings,
  onAddSection,
  onAddField,
  onOpenFieldTypesInfo,
}: {
  kind: TemplateKind;
  section: StationSection | null;
  selection: BuilderSelection;
  dropTarget: { sectionId: string; index: number } | null;
  sectionIndex: number;
  sectionCount: number;
  onStepSection: (delta: -1 | 1) => void;
  canUndo: boolean;
  canRedo: boolean;
  onUndo: () => void;
  onRedo: () => void;
  onSelectBlock: (sectionId: string, blockId: string) => void;
  onSectionTitleChange: (sectionId: string, title: string) => void;
  onSectionDescriptionChange: (sectionId: string, description: string) => void;
  onOpenSectionSettings: (sectionId: string) => void;
  onAddSection: () => void;
  onAddField: (type: StationBlockType, sectionId: string, index?: number) => void;
  onOpenFieldTypesInfo: () => void;
  /** A published version: the toolbar (section stepping, undo) stays live, the fields and details do not. */
  readOnly?: boolean;
}) {
  const w = useAssessWords();
  const { setNodeRef: setDropRef, isOver } = useDroppable({
    id: section ? `drop-section:${section.id}` : "drop-sections-end",
    disabled: !section,
  });

  if (!section) {
    return (
      <div className={`${boardPad} min-w-0 items-start`}>
        <p className="text-assess-label font-medium text-ink">Empty layout</p>
        <p className="text-assess-meta text-ink-subtle">
          {kind === "station"
            ? `A section is written for the patient, the candidate or the ${w.examiner}. Add one, then add the fields it needs.`
            : "Sections group related fields. Add one, then add the fields it needs one at a time."}
        </p>
        <button type="button" className={boardBtn("primary")} onClick={onAddSection}>
          Add your first section
        </button>
      </div>
    );
  }

  const count = section.blocks.length;
  const field = (type: StationBlockType, index?: number) => onAddField(type, section.id, index);

  return (
    <div className={`${boardPad} min-w-0 !border-osce-border !bg-surface-raised`}>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <span className="min-w-0 truncate text-assess-eyebrow uppercase text-ink-subtle">
          {section.title || "Untitled section"}
        </span>
        <div className="flex items-center gap-1.5">
          {sectionCount > 1 ? (
            <>
              <IconTool label="Previous section" disabled={sectionIndex <= 0} onClick={() => onStepSection(-1)}>
                <HiOutlineChevronLeft aria-hidden className="h-4 w-4" />
              </IconTool>
              <IconTool label="Next section" disabled={sectionIndex >= sectionCount - 1} onClick={() => onStepSection(1)}>
                <HiOutlineChevronRight aria-hidden className="h-4 w-4" />
              </IconTool>
              <span aria-hidden className="mx-1 h-5 w-px bg-osce-border" />
            </>
          ) : null}
          <IconTool label="Undo" disabled={!canUndo} onClick={onUndo}>
            <HiOutlineArrowUturnLeft aria-hidden className="h-4 w-4" />
          </IconTool>
          <IconTool label="Redo" disabled={!canRedo} onClick={onRedo}>
            <HiOutlineArrowUturnRight aria-hidden className="h-4 w-4" />
          </IconTool>
        </div>
      </div>
      <fieldset disabled={readOnly} className="contents">
      <div className={`${boardCard} flex flex-col gap-3 p-4`}>
        <p className="text-assess-eyebrow uppercase text-ink-subtle">Section details</p>
      <input
        value={section.title}
        onChange={(e) => onSectionTitleChange(section.id, e.target.value)}
        className={boardInput}
        placeholder="Section title"
        aria-label="Section title"
      />
      <input
        value={section.description ?? ""}
        onChange={(e) => onSectionDescriptionChange(section.id, e.target.value)}
        className={boardInput}
        placeholder="Add a short description (optional)"
        aria-label="Section description"
      />
      <button
        type="button"
        className={`${boardButtonSmall} inline-flex items-center gap-1.5 self-start`}
        onClick={() => onOpenSectionSettings(section.id)}
      >
        <HiOutlineCog6Tooth aria-hidden className="h-4 w-4" />
        Section settings
      </button>
      </div>
      <p className="-mb-1.5 text-assess-eyebrow uppercase text-ink-subtle">Fields</p>

      <section
        ref={setDropRef}
        aria-label="Fields"
        className={`${boardCardClipped} ${isOver ? "bg-osce-accent-muted" : ""}`}
      >
        {count === 0 ? (
          <div className="px-5 py-3.5 text-assess-label">
            <p className="font-medium text-ink">Empty section</p>
            <p className="text-assess-meta text-ink-subtle">No fields yet. Add the first one below.</p>
          </div>
        ) : (
          <SortableContext items={section.blocks.map((b) => blockDragId(section.id, b.id))} strategy={verticalListSortingStrategy}>
            {section.blocks.map((block, blockIndex) => (
              <CanvasBlock
                key={block.id}
                kind={kind}
                section={section}
                block={block}
                first={blockIndex === 0}
                selected={selection.kind === "block" && selection.blockId === block.id && selection.sectionId === section.id}
                isDropBefore={dropTarget?.sectionId === section.id && dropTarget.index === blockIndex}
                insertAbove={
                  blockIndex > 0 ? (
                    <InsertFieldBetween
                      kind={kind}
                      onPick={(type) => field(type, blockIndex)}
                      onOpenFieldTypesInfo={onOpenFieldTypesInfo}
                    />
                  ) : undefined
                }
                onSelect={() => onSelectBlock(section.id, block.id)}
              />
            ))}
          </SortableContext>
        )}
        {dropTarget?.sectionId === section.id && dropTarget.index >= count ? (
          <div className="mx-4 h-0.5 rounded-full bg-osce-accent" />
        ) : null}
      </section>
      <AddFieldPanel kind={kind} onPick={(type) => field(type)} onOpenFieldTypesInfo={onOpenFieldTypesInfo} />
      </fieldset>
    </div>
  );
}
