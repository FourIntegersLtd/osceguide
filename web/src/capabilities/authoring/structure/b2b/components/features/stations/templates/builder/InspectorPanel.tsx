"use client";

import { BlockInspector } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/inspector/BlockInspector";
import type { BuilderSelection } from "@/capabilities/authoring/structure/b2b/lib/stations/structureBuilderOps";
import {
  changeBlockType,
  duplicateBlock,
  removeBlock,
  updateBlock,
} from "@/capabilities/authoring/structure/b2b/lib/stations/structureBuilderOps";
import type { TemplateKind } from "@/capabilities/authoring/structure/b2b/lib/stations/blockTypeLabels";
import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { boardPad } from "@/foundation/ui/boardKit";

/**
 * The board's field inspector, always on screen: the settings of the selected field (the section's first
 * field until one is picked). Section settings open in a dialog from the section card.
 */
export function InspectorPanel({
  kind,
  value,
  activeSectionId,
  selection,
  onChange,
  onSelectionChange,
  blockHints,
  profileGuidesLoading,
}: {
  kind: TemplateKind;
  value: StationStructure;
  activeSectionId: string | null;
  selection: BuilderSelection;
  onChange: (next: StationStructure) => void;
  onSelectionChange: (next: BuilderSelection) => void;
  blockHints?: Record<string, string>;
  profileGuidesLoading?: boolean;
}) {
  const section = value.sections.find((s) => s.id === activeSectionId);
  if (!section) return null;
  const block =
    (selection.kind === "block" && selection.sectionId === section.id
      ? section.blocks.find((b) => b.id === selection.blockId)
      : undefined) ?? section.blocks[0];

  return (
    <>
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
