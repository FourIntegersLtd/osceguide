"use client";

import { BlockInspector } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/inspector/BlockInspector";
import { SectionInspector } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/inspector/SectionInspector";
import type { BuilderSelection } from "@/capabilities/authoring/structure/b2b/lib/stations/structureBuilderOps";
import {
  changeBlockType,
  duplicateBlock,
  removeBlock,
  setSectionAudience,
  updateBlock,
  updateSection,
} from "@/capabilities/authoring/structure/b2b/lib/stations/structureBuilderOps";
import { audienceMeta, sectionAudience } from "@/capabilities/authoring/structure/b2b/lib/stations/blockRoles";
import type { TemplateKind } from "@/capabilities/authoring/structure/b2b/lib/stations/blockTypeLabels";
import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { boardPad } from "@/foundation/ui/boardKit";

/**
 * The board's two inspector cards, always on screen: the active section's settings and, under it, the
 * settings of the selected field (the section's first field until one is picked).
 */
export function InspectorPanel({
  kind,
  value,
  activeSectionId,
  selection,
  onChange,
  onSelectionChange,
  onRemoveSection,
  blockHints,
  profileGuidesLoading,
}: {
  kind: TemplateKind;
  value: StationStructure;
  activeSectionId: string | null;
  selection: BuilderSelection;
  onChange: (next: StationStructure) => void;
  onSelectionChange: (next: BuilderSelection) => void;
  onRemoveSection: (sectionId: string) => void;
  blockHints?: Record<string, string>;
  profileGuidesLoading?: boolean;
}) {
  const section = value.sections.find((s) => s.id === activeSectionId);
  if (!section) return null;
  const sectionIndex = value.sections.indexOf(section);
  const block =
    (selection.kind === "block" && selection.sectionId === section.id
      ? section.blocks.find((b) => b.id === selection.blockId)
      : undefined) ?? section.blocks[0];

  return (
    <>
      <section className={boardPad} aria-label="Section settings">
        <h2 className="text-assess-state-title font-semibold text-ink">Section</h2>
        <SectionInspector
          kind={kind}
          section={section}
          caption={kind === "station" ? audienceMeta(sectionAudience(section)).label : `Section ${sectionIndex + 1}`}
          onPatch={(patch) => onChange(updateSection(value, section.id, patch))}
          onAudienceChange={(next) => onChange(setSectionAudience(value, section.id, next))}
          onRemove={() => onRemoveSection(section.id)}
        />
      </section>
      {block ? (
        <section key={block.id} className={boardPad} aria-label="Field settings">
          <h2 className="text-assess-state-title font-semibold text-ink">Field</h2>
          <BlockInspector
            kind={kind}
            block={block}
            section={section}
            blockHints={blockHints}
            profileGuidesLoading={profileGuidesLoading}
            onPatch={(patch) => onChange(updateBlock(value, section.id, block.id, patch))}
            onChangeType={(type) => onChange(changeBlockType(value, section.id, block.id, type))}
            onDuplicate={() => onChange(duplicateBlock(value, section.id, block.id))}
            onRemove={() => {
              onChange(removeBlock(value, section.id, block.id));
              onSelectionChange({ kind: "section", sectionId: section.id });
            }}
          />
        </section>
      ) : null}
    </>
  );
}
