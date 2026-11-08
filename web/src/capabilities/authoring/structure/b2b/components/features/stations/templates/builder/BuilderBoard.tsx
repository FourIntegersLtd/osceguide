"use client";

import type { ReactNode } from "react";
import { InspectorPanel } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/InspectorPanel";
import { SectionChipStrip, SectionOutline } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/SectionFilmstrip";
import { SectionStage } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/SectionStage";
import { TemplateGenerationPanel } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/TemplateGenerationPanel";
import type { useStructureBuilder } from "@/capabilities/authoring/structure/b2b/hooks/stations/useStructureBuilder";
import { useStationGenerationProfile } from "@/capabilities/authoring/structure/b2b/hooks/stations/useStationGenerationProfile";
import { updateSection } from "@/capabilities/authoring/structure/b2b/lib/stations/structureBuilderOps";
import type { TemplateKind } from "@/capabilities/authoring/structure/b2b/lib/stations/blockTypeLabels";
import { profileKeyForExamCode } from "@/capabilities/authoring/structure/b2b/lib/stations/generationProfileKeys";
import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { boardCols, boardColsMain, boardColsRail } from "@/foundation/ui/boardKit";

/** Greys out and disables everything inside it (a published version's fields) while leaving the rest of the page live. */
function Frozen({ frozen, children }: { frozen: boolean; children: ReactNode }) {
  return (
    <fieldset disabled={frozen} className={`min-w-0 border-0 p-0${frozen ? " opacity-70" : ""}`}>
      {children}
    </fieldset>
  );
}

/**
 * The Build view's three columns: a sections card beside the active section's card (its fields and the
 * add-field fold), the AI-drafting fold below them, and a permanent field inspector in the right-hand rail
 * (under the rest on a phone). Section navigation stays live when `readOnly`; undo and redo are no-ops there.
 */
export function BuilderBoard({
  kind,
  value,
  builder,
  examCode,
  allowCustomGenerationPrompt,
  readOnly,
  onOpenSectionSettings,
  onOpenFieldTypesInfo,
}: {
  kind: TemplateKind;
  value: StationStructure;
  builder: ReturnType<typeof useStructureBuilder>;
  examCode?: string | null;
  allowCustomGenerationPrompt: boolean;
  readOnly: boolean;
  onOpenSectionSettings: (sectionId: string) => void;
  onOpenFieldTypesInfo: () => void;
}) {
  const activeSection = value.sections.find((s) => s.id === builder.activeSectionId) ?? null;
  const activeSectionIndex = value.sections.findIndex((s) => s.id === builder.activeSectionId);
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
    readOnly,
  };
  const generationProfile = useStationGenerationProfile(
    kind === "station" ? (value.generation?.profileKey ?? profileKeyForExamCode(examCode)) : undefined,
  );

  return (
    <div className={`${boardCols} min-w-0`}>
      <div className={boardColsMain}>
        <SectionChipStrip {...sectionNav} />
        <div className="grid items-start gap-4 lg:grid-cols-[220px_1fr]">
          <div className="hidden lg:block">
            <SectionOutline {...sectionNav} />
          </div>
          <SectionStage
            kind={kind}
            readOnly={readOnly}
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
            canUndo={builder.canUndo && !readOnly}
            canRedo={builder.canRedo && !readOnly}
            onUndo={builder.undo}
            onRedo={builder.redo}
            onSelectBlock={(sectionId, blockId) => builder.setSelection({ kind: "block", sectionId, blockId })}
            onSectionTitleChange={(sectionId, title) => builder.applyChange(updateSection(value, sectionId, { title }))}
            onSectionDescriptionChange={(sectionId, description) =>
              builder.applyChange(updateSection(value, sectionId, { description: description || undefined }))
            }
            onOpenSectionSettings={onOpenSectionSettings}
            onAddSection={builder.handleAddSection}
            onAddField={(type, sectionId, index) => builder.addBlockToTarget(type, sectionId, index)}
            onOpenFieldTypesInfo={onOpenFieldTypesInfo}
          />
        </div>
        {kind === "station" ? (
          <Frozen frozen={readOnly}>
            <TemplateGenerationPanel
              value={value}
              onChange={builder.applyChange}
              examCode={examCode}
              allowCustomSystemPrompt={allowCustomGenerationPrompt}
              systemPrompt={generationProfile.systemPrompt}
              profileGuidesLoading={generationProfile.loading}
              profileGuidesError={generationProfile.error}
            />
          </Frozen>
        ) : null}
      </div>
      <div className={`${boardColsRail} min-w-0`}>
        <Frozen frozen={readOnly}>
          <InspectorPanel
            kind={kind}
            value={value}
            activeSectionId={builder.activeSectionId}
            selection={builder.selection}
            onChange={builder.applyChange}
            onSelectionChange={builder.setSelection}
            blockHints={generationProfile.blockHints}
            profileGuidesLoading={generationProfile.loading}
          />
        </Frozen>
      </div>
    </div>
  );
}
