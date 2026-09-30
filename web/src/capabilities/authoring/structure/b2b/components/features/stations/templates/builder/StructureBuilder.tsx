"use client";

import { Select } from "@/foundation/ui";
import { useState } from "react";
import { DndContext, DragOverlay, closestCenter } from "@dnd-kit/core";
import { InspectorPanel } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/InspectorPanel";
import {
  SectionChipStrip,
  SectionOutline,
} from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/SectionFilmstrip";
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
import { TemplateBuilderShell } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/TemplateBuilderShell";
import { TemplateGenerationPanel } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/TemplateGenerationPanel";
import {
  BuilderChromeProvider,
  BuilderIconButton,
  builderUi,
} from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/builderChrome";
import { HiArrowUturnLeft, HiArrowUturnRight } from "react-icons/hi2";

/**
 * Section-at-a-time structure editor: an outline of sections (left, from
 * `lg`; a chip strip above the stage below that), the active section's
 * fields in the middle, and settings for the selected item in a drawer.
 * Fields are added from a grouped menu in the stage; drag is for reordering.
 *
 * `kind="station"` colours sections by who reads them (patient, candidate,
 * examiner) and gives each field a role the engine places it by;
 * `kind="feedback"` is a plain marking form with the scoring field types.
 */
export function StructureBuilder({
  value,
  onChange,
  title,
  onTitleChange,
  kind = "station",
  flatChrome = false,
  examCode,
  allowCustomGenerationPrompt = false,
}: {
  value: StationStructure;
  onChange: (next: StationStructure) => void;
  title?: string;
  onTitleChange?: (title: string) => void;
  kind?: TemplateKind;
  /** @deprecated One palette serves both arms now. */
  flatChrome?: boolean;
  examCode?: string | null;
  allowCustomGenerationPrompt?: boolean;
}) {
  const [fieldTypesInfoOpen, setFieldTypesInfoOpen] = useState(false);
  const builder = useStructureBuilder({ value, onChange });

  const activeSection =
    value.sections.find((s) => s.id === builder.activeSectionId) ?? null;
  const activeSectionIndex = activeSection
    ? value.sections.findIndex((s) => s.id === activeSection.id)
    : -1;

  const activeParsed = builder.activeDragId
    ? parseDragId(builder.activeDragId)
    : null;

  const activeBlock =
    activeParsed?.kind === "block" && activeParsed.sectionId
      ? value.sections
          .find((s) => s.id === activeParsed.sectionId)
          ?.blocks.find((b) => b.id === activeParsed.blockId)
      : null;

  const stepSection = (delta: -1 | 1) => {
    const next = value.sections[activeSectionIndex + delta];
    if (next) builder.focusSection(next.id);
  };

  const sectionNav = {
    kind,
    sections: value.sections,
    activeSectionId: builder.activeSectionId,
    onFocusSection: builder.focusSection,
    onAddSection: builder.handleAddSection,
  };

  const persona = value.layout?.persona ?? "patient";

  const generationProfileKey =
    value.generation?.profileKey ?? profileKeyForExamCode(examCode);
  const generationProfile = useStationGenerationProfile(
    kind === "station" ? generationProfileKey : undefined,
  );

  return (
    <BuilderChromeProvider lightGray={flatChrome}>
      <DndContext
        sensors={builder.sensors}
        collisionDetection={closestCenter}
        onDragStart={builder.handleDragStart}
        onDragOver={builder.handleDragOver}
        onDragEnd={builder.handleDragEnd}
        onDragCancel={builder.handleDragCancel}
      >
        <TemplateBuilderShell
          title={title}
          onTitleChange={onTitleChange}
          subheader={
            <>
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
              <SectionChipStrip {...sectionNav} />
            </>
          }
          toolbarActions={
            <>
              {kind === "station" ? (
                <label className="mr-2 hidden items-center gap-2 text-osce-caption text-ink-muted sm:inline-flex">
                  Who speaks in the AI role
                  <Select
                    value={persona}
                    selectSize="sm"
                    className="w-auto"
                    onChange={(e) =>
                      builder.applyChange({
                        ...value,
                        layout: {
                          ...value.layout,
                          persona: e.target.value as "patient" | "examiner",
                        },
                      })
                    }
                  >
                    <option value="patient">the patient</option>
                    <option value="examiner">the examiner (viva)</option>
                  </Select>
                </label>
              ) : null}
              <BuilderIconButton
                label="Undo"
                disabled={!builder.canUndo}
                onClick={builder.undo}
              >
                <HiArrowUturnLeft aria-hidden />
              </BuilderIconButton>
              <BuilderIconButton
                label="Redo"
                disabled={!builder.canRedo}
                onClick={builder.redo}
              >
                <HiArrowUturnRight aria-hidden />
              </BuilderIconButton>
            </>
          }
        >
          <SectionOutline {...sectionNav} />
          <SectionStage
            kind={kind}
            section={activeSection}
            sectionIndex={activeSectionIndex}
            sections={value.sections}
            selection={builder.selection}
            dropTarget={
              builder.dropTarget?.kind === "section"
                ? {
                    sectionId: builder.dropTarget.sectionId,
                    index: builder.dropTarget.index,
                  }
                : null
            }
            onSelectNone={() => builder.setSelection({ kind: "none" })}
            onSelectBlock={(sectionId, blockId) =>
              builder.setSelection({ kind: "block", sectionId, blockId })
            }
            onSectionTitleChange={(sectionId, nextTitle) =>
              builder.applyChange(
                updateSection(value, sectionId, { title: nextTitle }),
              )
            }
            onSectionDescriptionChange={(sectionId, description) =>
              builder.applyChange(
                updateSection(value, sectionId, {
                  description: description || undefined,
                }),
              )
            }
            onOpenSectionSettings={builder.openSectionSettings}
            onAddSection={builder.handleAddSection}
            onAddField={(type, sectionId, index) =>
              builder.addBlockToTarget(type, sectionId, index)
            }
            onOpenFieldTypesInfo={() => setFieldTypesInfoOpen(true)}
            onStepSection={stepSection}
          />
          <InspectorPanel
            kind={kind}
            value={value}
            selection={builder.selection}
            onChange={builder.applyChange}
            onSelectionChange={builder.setSelection}
            onRemoveSection={builder.handleRemoveSection}
            blockHints={generationProfile.blockHints}
            profileGuidesLoading={generationProfile.loading}
          />
        </TemplateBuilderShell>
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
