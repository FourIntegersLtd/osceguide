"use client";

import type { ReactNode } from "react";
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
import { formsMetaForStationBlockType, type TemplateKind } from "@/capabilities/authoring/structure/b2b/lib/stations/blockTypeLabels";
import { audienceMeta, sectionAudience } from "@/capabilities/authoring/structure/b2b/lib/stations/blockRoles";
import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { HiOutlineRectangleStack, HiOutlineXMark } from "react-icons/hi2";
import {
  BuilderIconButton,
  builderUi,
  ToneBadge,
  toneForAudience,
  toneForIndex,
  TypeBadge,
} from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/builderChrome";

/**
 * Settings for the selected field or section. A right-hand column from `lg`
 * up; below that it overlays the stage as a drawer with a scrim.
 */
export function InspectorPanel({
  kind,
  value,
  selection,
  onChange,
  onSelectionChange,
  onRemoveSection,
  blockHints,
  profileGuidesLoading,
}: {
  kind: TemplateKind;
  value: StationStructure;
  selection: BuilderSelection;
  onChange: (next: StationStructure) => void;
  onSelectionChange: (next: BuilderSelection) => void;
  onRemoveSection: (sectionId: string) => void;
  blockHints?: Record<string, string>;
  profileGuidesLoading?: boolean;
}) {
  if (selection.kind === "none") return null;

  const close = () => onSelectionChange({ kind: "none" });

  if (selection.kind === "block") {
    const section = value.sections.find((s) => s.id === selection.sectionId);
    const block = section?.blocks.find((b) => b.id === selection.blockId);
    if (!section || !block) return null;
    const meta = formsMetaForStationBlockType(block.type);
    const TypeIcon = meta.icon;

    return (
      <Drawer
        key={block.id}
        title="Field"
        subtitle={meta.formsLabel}
        icon={
          <TypeBadge className="bg-osce-accent-muted text-osce-accent">
            <TypeIcon aria-hidden />
          </TypeBadge>
        }
        onClose={close}
      >
        <BlockInspector
          kind={kind}
          block={block}
          section={section}
          blockHints={blockHints}
          profileGuidesLoading={profileGuidesLoading}
          onPatch={(patch) =>
            onChange(updateBlock(value, section.id, block.id, patch))
          }
          onChangeType={(type) =>
            onChange(changeBlockType(value, section.id, block.id, type))
          }
          onDuplicate={() =>
            onChange(duplicateBlock(value, section.id, block.id))
          }
          onRemove={() => {
            onChange(removeBlock(value, section.id, block.id));
            onSelectionChange({ kind: "section", sectionId: section.id });
          }}
        />
      </Drawer>
    );
  }

  const sectionIndex = value.sections.findIndex(
    (s) => s.id === selection.sectionId,
  );
  const section = value.sections[sectionIndex];
  if (!section) return null;
  const audience = kind === "station" ? audienceMeta(sectionAudience(section)) : null;
  const SectionIcon = audience ? audience.icon : HiOutlineRectangleStack;

  return (
    <Drawer
      key={section.id}
      title="Section"
      subtitle={audience ? audience.label : `Section ${sectionIndex + 1}`}
      icon={
        <ToneBadge tone={audience ? toneForAudience[audience.id] : toneForIndex(sectionIndex)}>
          <SectionIcon aria-hidden />
        </ToneBadge>
      }
      onClose={close}
    >
      <SectionInspector
        kind={kind}
        section={section}
        onPatch={(patch) => onChange(updateSection(value, section.id, patch))}
        onAudienceChange={(next) => onChange(setSectionAudience(value, section.id, next))}
        onRemove={() => onRemoveSection(section.id)}
      />
    </Drawer>
  );
}

function Drawer({
  title,
  subtitle,
  icon,
  onClose,
  children,
}: {
  title: string;
  subtitle?: string;
  icon: ReactNode;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <>
      <button
        type="button"
        aria-label="Close settings"
        onClick={onClose}
        className="absolute inset-0 z-20 bg-ink/15 backdrop-blur-[1px] lg:hidden"
      />
      {/* Stops a click inside reaching the canvas's deselect; not an action. */}
      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-noninteractive-element-interactions */}
      <aside
        role="dialog"
        aria-label={`${title} settings`}
        className={[
          "osce-builder-in absolute inset-y-0 right-0 z-30 flex w-[min(340px,92%)] flex-col shadow-2xl",
          "lg:static lg:z-auto lg:w-[340px] lg:shrink-0 lg:self-stretch lg:shadow-none",
          builderUi.surface,
          builderUi.l,
        ].join(" ")}
        onClick={(e) => e.stopPropagation()}
      >
        <div className={`flex items-center gap-3 px-4 py-3.5 ${builderUi.b}`}>
          {icon}
          <div className="min-w-0 flex-1">
            <p className="truncate text-osce-body font-semibold text-ink-muted">
              {title}
            </p>
            {subtitle ? (
              <p className="truncate text-osce-caption text-ink-subtle">
                {subtitle}
              </p>
            ) : null}
          </div>
          <BuilderIconButton label="Close settings" onClick={onClose}>
            <HiOutlineXMark aria-hidden />
          </BuilderIconButton>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">{children}</div>
      </aside>
    </>
  );
}
