"use client";

import { useState } from "react";
import { DndContext, DragOverlay, closestCenter } from "@dnd-kit/core";
import { BoardTabBar, boardTabId } from "@/foundation/ui/BoardTabBar";
import { BlockPreviewContent } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/BlockPreviewContent";
import { BuilderChromeProvider, builderUi } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/builderChrome";
import { BuilderBoard } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/BuilderBoard";
import { SectionSettingsDialog } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/SectionSettingsDialog";
import { TemplatePreview } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/TemplatePreview";
import { StationBlockTypesInfoModal } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/StationBlockTypesInfoModal";
import { useStructureBuilder } from "@/capabilities/authoring/structure/b2b/hooks/stations/useStructureBuilder";
import type { TemplateKind } from "@/capabilities/authoring/structure/b2b/lib/stations/blockTypeLabels";
import { parseDragId, setSectionAudience } from "@/capabilities/authoring/structure/b2b/lib/stations/structureBuilderOps";
import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";

type BuilderView = "build" | "preview";
const BUILDER_VIEWS: { id: BuilderView; label: string }[] = [
  { id: "build", label: "Build" },
  { id: "preview", label: "Preview" },
];
const TABS = { idPrefix: "builder-tab", panelId: "builder-view-panel" } as const;

/**
 * The template builder: a Build / Preview switch over the board (`BuilderBoard`), with drag-and-drop, the
 * section settings dialog and the field-type guide around it.
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
  readOnly = false,
}: {
  value: StationStructure;
  onChange: (next: StationStructure) => void;
  kind?: TemplateKind;
  examCode?: string | null;
  allowCustomGenerationPrompt?: boolean;
  /** A published or retired version: the fields cannot change, but the Build and Preview tabs still work. */
  readOnly?: boolean;
}) {
  const [fieldTypesInfoOpen, setFieldTypesInfoOpen] = useState(false);
  /** The section whose settings dialog is open; it closes on its own if that section goes away. */
  const [settingsSectionId, setSettingsSectionId] = useState<string | null>(null);
  const [view, setView] = useState<BuilderView>("build");
  const builder = useStructureBuilder({ value, onChange, readOnly });

  const dragged = builder.activeDragId ? parseDragId(builder.activeDragId) : null;
  const activeBlock =
    dragged?.kind === "block" && dragged.sectionId
      ? value.sections.find((s) => s.id === dragged.sectionId)?.blocks.find((b) => b.id === dragged.blockId)
      : null;
  const settingsIndex = value.sections.findIndex((s) => s.id === settingsSectionId);
  const settingsSection = settingsIndex >= 0 ? value.sections[settingsIndex] : undefined;

  return (
    <BuilderChromeProvider>
      <DndContext
        sensors={readOnly ? [] : builder.sensors}
        collisionDetection={closestCenter}
        onDragStart={builder.handleDragStart}
        onDragOver={builder.handleDragOver}
        onDragEnd={builder.handleDragEnd}
        onDragCancel={builder.handleDragCancel}
      >
        <BoardTabBar label="Builder view" {...TABS} tabs={BUILDER_VIEWS} value={view} onChange={setView} className="mb-5" />
        <div role="tabpanel" id={TABS.panelId} aria-labelledby={boardTabId(TABS.idPrefix, view)}>
          {view === "preview" ? (
            <TemplatePreview kind={kind} value={value} />
          ) : (
            <BuilderBoard
              kind={kind}
              value={value}
              builder={builder}
              examCode={examCode}
              allowCustomGenerationPrompt={allowCustomGenerationPrompt}
              readOnly={readOnly}
              onOpenSectionSettings={(sectionId) => {
                builder.focusSection(sectionId);
                setSettingsSectionId(sectionId);
              }}
              onOpenFieldTypesInfo={() => setFieldTypesInfoOpen(true)}
            />
          )}
        </div>
        <DragOverlay dropAnimation={null}>
          {activeBlock ? (
            <div className={`w-[320px] rounded-xl px-3 py-2 shadow-lg backdrop-blur-sm ${builderUi.box} bg-osce-surface/95`}>
              <BlockPreviewContent block={activeBlock} minimal />
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>
      {!readOnly && settingsSection ? (
        <SectionSettingsDialog
          kind={kind}
          section={settingsSection}
          index={settingsIndex}
          onAudienceChange={(next) => builder.applyChange(setSectionAudience(value, settingsSection.id, next))}
          onRemove={() => {
            setSettingsSectionId(null);
            builder.handleRemoveSection(settingsSection.id);
          }}
          onClose={() => setSettingsSectionId(null)}
        />
      ) : null}
      <StationBlockTypesInfoModal kind={kind} open={fieldTypesInfoOpen} onClose={() => setFieldTypesInfoOpen(false)} />
    </BuilderChromeProvider>
  );
}
