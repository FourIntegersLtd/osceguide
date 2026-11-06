"use client";

import { useDroppable } from "@dnd-kit/core";
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
import { boardBtn, boardCardClipped, boardInput, boardPad, boardButtonSmall } from "@/foundation/ui/boardKit";

/** The board's section card: the section's name and description, its fields in a list, and the add-field fold. */
export function SectionStage({
  kind,
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
}) {
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
            ? "A section is written for the patient, the candidate or the examiner. Add one, then add the fields it needs."
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
    <div className={`${boardPad} min-w-0`}>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <span className="min-w-0 truncate text-assess-eyebrow uppercase text-ink-subtle">
          {section.title || "Untitled section"}
        </span>
        <span>
          {sectionCount > 1 ? (
            <>
              <button type="button" className={boardBtn("ghost", true)} disabled={sectionIndex <= 0} onClick={() => onStepSection(-1)}>
                Previous section
              </button>
              <button type="button" className={boardBtn("ghost", true)} disabled={sectionIndex >= sectionCount - 1} onClick={() => onStepSection(1)}>
                Next section
              </button>
            </>
          ) : null}
          <button type="button" className={boardBtn("ghost", true)} disabled={!canUndo} onClick={onUndo}>
            Undo
          </button>
          <button type="button" className={boardBtn("ghost", true)} disabled={!canRedo} onClick={onRedo}>
            Redo
          </button>
        </span>
      </div>
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
        className={`${boardButtonSmall} self-start`}
        onClick={() => onOpenSectionSettings(section.id)}
      >
        Section settings
      </button>

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
    </div>
  );
}
