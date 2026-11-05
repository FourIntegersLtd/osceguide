"use client";

import { useMemo, type ComponentType, type ReactNode } from "react";
import {
  HiCheck,
  HiOutlineAcademicCap,
  HiOutlineBeaker,
  HiOutlineChatBubbleLeftRight,
  HiOutlineClipboardDocumentList,
  HiOutlineDocument,
} from "react-icons/hi2";
import { structureFromStartPoint } from "@/capabilities/authoring/structure/b2b/lib/stations/stationTemplatePresets";
import {
  orderedStartOptions,
  type StationTemplateStartOption,
} from "@/capabilities/authoring/structure/b2b/lib/stations/stationTemplateStartOptions";
import type {
  StationStructure,
  StationTemplateStartPoint,
} from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { B2BIconChip } from "@/capabilities/authoring/structure/b2b/components/ui/B2BIconChip";
import {
  b2bBuilderCardSelected,
  b2bEyebrow,
  b2bInputBase,
  type B2BChipHue,
} from "@/capabilities/authoring/structure/b2b/theme/b2bUi";

const START_POINT_ICONS: Record<
  StationTemplateStartPoint,
  ComponentType<{
    className?: string;
    "aria-hidden"?: boolean | "true" | "false";
  }>
> = {
  blank: HiOutlineDocument,
  asterix: HiOutlineBeaker,
  sca: HiOutlineChatBubbleLeftRight,
  plab: HiOutlineAcademicCap,
  casc: HiOutlineChatBubbleLeftRight,
  ortho: HiOutlineClipboardDocumentList,
  ortho_prioritisation: HiOutlineClipboardDocumentList,
  ortho_communication: HiOutlineChatBubbleLeftRight,
  ortho_portfolio: HiOutlineAcademicCap,
};

const START_POINT_HUES: Record<StationTemplateStartPoint, B2BChipHue> = {
  blank: "teal",
  asterix: "amber",
  sca: "blue",
  plab: "violet",
  casc: "green",
  ortho: "amber",
  ortho_prioritisation: "rose",
  ortho_communication: "teal",
  ortho_portfolio: "violet",
};

function GalleryCard({
  option,
  selected,
  onSelect,
  resolveStructure,
}: {
  option: ReturnType<typeof orderedStartOptions>[number];
  selected: boolean;
  onSelect: () => void;
  resolveStructure: (startPoint: StationTemplateStartPoint) => StationStructure;
}) {
  const structure = useMemo(
    () => resolveStructure(option.id),
    [option.id, resolveStructure],
  );
  const sectionCount = structure.sections.length;
  const CardIcon = START_POINT_ICONS[option.id];

  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      aria-label={`${option.title}. ${option.description}. ${sectionCount} sections.`}
      onClick={onSelect}
      className={[
        "flex w-full min-w-0 items-start gap-3 rounded-osce-lg p-3 text-left transition-colors",
        selected
          ? b2bBuilderCardSelected
          : "border border-osce-border bg-osce-surface hover:bg-osce-canvas",
        "focus:outline-none focus-visible:border-osce-accent",
      ].join(" ")}
    >
      <B2BIconChip icon={CardIcon} hue={START_POINT_HUES[option.id]} size="sm" />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="min-w-0 flex-1 truncate text-osce-body font-medium text-ink">
            {option.title}
          </span>
          {option.recommended ? (
            <span className="shrink-0 text-osce-caption font-medium text-osce-accent">Recommended</span>
          ) : null}
          {selected ? (
            <HiCheck className="h-4 w-4 shrink-0 text-osce-accent" aria-hidden />
          ) : null}
        </div>
        <p className="mt-0.5 truncate text-osce-caption text-ink-muted">
          {option.description}
        </p>
        <p className="mt-1 text-osce-caption text-ink-subtle">
          {sectionCount} {sectionCount === 1 ? "section" : "sections"}
        </p>
      </div>
    </button>
  );
}

export function TemplateLayoutGallery({
  orgSlug,
  options,
  value,
  onChange,
  sectionLabel = "Layouts",
  resolveStructure = structureFromStartPoint,
}: {
  orgSlug: string;
  options: readonly StationTemplateStartOption[];
  value: StationTemplateStartPoint;
  onChange: (next: StationTemplateStartPoint) => void;
  sectionLabel?: string;
  embedded?: boolean;
  resolveStructure?: (startPoint: StationTemplateStartPoint) => StationStructure;
}) {
  const orderedOptions = useMemo(
    () => orderedStartOptions(orgSlug, options),
    [orgSlug, options],
  );

  return (
    <div className="w-full">
      <p className={[b2bEyebrow, "mb-3"].join(" ")}>{sectionLabel}</p>
      <div
        role="radiogroup"
        aria-label={sectionLabel}
        className="grid w-full grid-cols-1 gap-2 sm:grid-cols-2"
      >
        {orderedOptions.map((option) => (
          <GalleryCard
            key={option.id}
            option={option}
            selected={value === option.id}
            onSelect={() => onChange(option.id)}
            resolveStructure={resolveStructure}
          />
        ))}
      </div>
    </div>
  );
}

export function TemplateStartPanel({
  orgSlug,
  title,
  onTitleChange,
  startPoint,
  onStartPointChange,
  options,
  resolveStructure = structureFromStartPoint,
  layoutSectionLabel,
  layoutHint,
  examField,
}: {
  orgSlug: string;
  title: string;
  onTitleChange: (title: string) => void;
  startPoint: StationTemplateStartPoint;
  onStartPointChange: (next: StationTemplateStartPoint) => void;
  options: readonly StationTemplateStartOption[];
  resolveStructure?: (startPoint: StationTemplateStartPoint) => StationStructure;
  layoutSectionLabel?: string;
  layoutHint?: string;
  examField?: ReactNode;
}) {
  const titleField = (
    <div className="space-y-1">
      <label
        htmlFor="b2b-template-start-title"
        className="text-osce-caption font-medium text-ink-muted"
      >
        Template title
      </label>
      <input
        id="b2b-template-start-title"
        value={title}
        onChange={(e) => onTitleChange(e.target.value)}
        className={b2bInputBase}
        placeholder="Untitled template"
        autoComplete="off"
      />
    </div>
  );

  return (
    <div className="space-y-5">
      {examField ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {examField}
          {titleField}
        </div>
      ) : (
        titleField
      )}
      {layoutHint ? (
        <p className="text-osce-caption text-ink-muted">{layoutHint}</p>
      ) : null}
      <TemplateLayoutGallery
        orgSlug={orgSlug}
        options={options}
        value={startPoint}
        onChange={onStartPointChange}
        resolveStructure={resolveStructure}
        embedded
        sectionLabel={layoutSectionLabel}
      />
    </div>
  );
}
