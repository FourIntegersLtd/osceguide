"use client";

import { useState } from "react";
import { DndContext, DragOverlay, closestCenter } from "@dnd-kit/core";
import { InspectorPanel } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/InspectorPanel";
import { SectionChipStrip, SectionOutline } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/SectionFilmstrip";
import { SectionStage } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/SectionStage";
import { BlockPreviewContent } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/BlockPreviewContent";
import { StationBlockTypesInfoModal } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/StationBlockTypesInfoModal";
import { useStructureBuilder } from "@/capabilities/authoring/structure/b2b/hooks/stations/useStructureBuilder";
import { useStationGenerationProfile } from "@/capabilities/authoring/structure/b2b/hooks/stations/useStationGenerationProfile";
import {
  parseDragId,
  updateSection,
} from "@/capabilities/authoring/structure/b2b/lib/stations/structureBuilderOps";
import type { TemplateKind } from "@/capabilities/authoring/structure/b2b/lib/stations/blockTypeLabels";
import { profileKeyForExamCode } from "@/capabilities/authoring/structure/b2b/lib/stations/generationProfileKeys";
import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { TemplateGenerationPanel } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/TemplateGenerationPanel";
import {
  BuilderChromeProvider,
  builderUi,
} from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/builderChrome";
import { boardCols, boardColsMain, boardColsRail } from "@/foundation/ui/boardKit";

/**
 * The board's three columns: a sections card beside the active section's card (its fields and the add-field
 * fold), the AI-drafting fold below them, and a permanent Section and Field inspector in the right-hand rail
 * (under the rest on a phone). Drag reorders sections and fields.
 *
 * `kind="station"` gives each section an audience and each field a role the engine places it by;
 * `kind="feedback"` is a plain marking form with the scoring field types.
 */
export function StructureBuilder({
  value,
  onChange,
  kind = "station",
  examCode,
  allowCustomGenerationPrompt = false,
}: {
  value: StationStructure;
  onChange: (next: StationStructure) => void;
  kind?: TemplateKind;
  examCode?: string | null;
  allowCustomGenerationPrompt?: boolean;
}) {
  const [fieldTypesInfoOpen, setFieldTypesInfoOpen] = useState(false);
  const builder = useStructureBuilder({ value, onChange });

  const activeSection =
    value.sections.find((s) => s.id === builder.activeSectionId) ?? null;

  const activeSectionIndex = value.sections.findIndex((s) => s.id === builder.activeSectionId);
  const stepSection = (delta: -1 | 1) => {
    const next = value.sections[activeSectionIndex + delta];
    if (next) builder.focusSection(next.id);
  };

  const activeParsed = builder.activeDragId
    ? parseDragId(builder.activeDragId)
    : null;

  const activeBlock =
    activeParsed?.kind === "block" && activeParsed.sectionId
      ? value.sections
          .find((s) => s.id === activeParsed.sectionId)
          ?.blocks.find((b) => b.id === activeParsed.blockId)
      : null;

  const sectionNav = {
    kind,
    sections: value.sections,
    activeSectionId: builder.activeSectionId,
    onFocusSection: builder.focusSection,
    onAddSection: builder.handleAddSection,
  };

  const generationProfileKey =
    value.generation?.profileKey ?? profileKeyForExamCode(examCode);
  const generationProfile = useStationGenerationProfile(
    kind === "station" ? generationProfileKey : undefined,
  );

  return (
    <BuilderChromeProvider>
      <DndContext
        sensors={builder.sensors}
        collisionDetection={closestCenter}
        onDragStart={builder.handleDragStart}
        onDragOver={builder.handleDragOver}
        onDragEnd={builder.handleDragEnd}
        onDragCancel={builder.handleDragCancel}
      >
        <div className={`${boardCols} !gap-5`}>
          <div className={`${boardColsMain} !gap-5`}>
            <SectionChipStrip {...sectionNav} />
            <div className="grid items-start gap-4 lg:grid-cols-[220px_1fr]">
              <div className="hidden lg:block">
                <SectionOutline {...sectionNav} />
              </div>
              <SectionStage
                kind={kind}
                section={activeSection}
                selection={builder.selection}
                dropTarget={
                  builder.dropTarget?.kind === "section"
                    ? { sectionId: builder.dropTarget.sectionId, index: builder.dropTarget.index }
                    : null
                }
                sectionIndex={activeSectionIndex}
                sectionCount={value.sections.length}
                onStepSection={stepSection}
                canUndo={builder.canUndo}
                canRedo={builder.canRedo}
                onUndo={builder.undo}
                onRedo={builder.redo}
                onSelectBlock={(sectionId, blockId) => builder.setSelection({ kind: "block", sectionId, blockId })}
                onSectionTitleChange={(sectionId, nextTitle) =>
                  builder.applyChange(updateSection(value, sectionId, { title: nextTitle }))
                }
                onSectionDescriptionChange={(sectionId, description) =>
                  builder.applyChange(updateSection(value, sectionId, { description: description || undefined }))
                }
                onOpenSectionSettings={(sectionId) => {
                  builder.openSectionSettings(sectionId);
                  document.getElementById("section-inspector-title")?.focus();
                }}
                onAddSection={builder.handleAddSection}
                onAddField={(type, sectionId, index) => builder.addBlockToTarget(type, sectionId, index)}
                onOpenFieldTypesInfo={() => setFieldTypesInfoOpen(true)}
              />
            </div>
            {kind === "station" ? (
              <TemplateGenerationPanel
                value={value}
                onChange={builder.applyChange}
                examCode={examCode}
                allowCustomSystemPrompt={allowCustomGenerationPrompt}
                systemPrompt={generationProfile.systemPrompt}
                profileGuidesLoading={generationProfile.loading}
                profileGuidesError={generationProfile.error}
              />
            ) : null}
          </div>
          <div className={`${boardColsRail} min-w-0 !gap-5`}>
            <InspectorPanel
              kind={kind}
              value={value}
              activeSectionId={builder.activeSectionId}
              selection={builder.selection}
              onChange={builder.applyChange}
              onSelectionChange={builder.setSelection}
              onRemoveSection={builder.handleRemoveSection}
              blockHints={generationProfile.blockHints}
              profileGuidesLoading={generationProfile.loading}
            />
          </div>
        </div>
        <DragOverlay dropAnimation={null}>
          {activeBlock ? (
            <div
              className={`w-[320px] rounded-xl px-3 py-2 shadow-lg backdrop-blur-sm ${builderUi.box} bg-osce-surface/95`}
            >
              <BlockPreviewContent block={activeBlock} minimal />
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>
      <StationBlockTypesInfoModal
        kind={kind}
        open={fieldTypesInfoOpen}
        onClose={() => setFieldTypesInfoOpen(false)}
      />
    </BuilderChromeProvider>
  );
}
