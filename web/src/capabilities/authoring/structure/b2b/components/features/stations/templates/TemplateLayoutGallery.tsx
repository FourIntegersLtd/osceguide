"use client";

import { useMemo, type ReactNode } from "react";
import { structureFromStartPoint } from "@/capabilities/authoring/structure/b2b/lib/stations/stationTemplatePresets";
import {
  orderedStartOptions,
  type StationTemplateStartOption,
} from "@/capabilities/authoring/structure/b2b/lib/stations/stationTemplateStartOptions";
import type {
  StationStructure,
  StationTemplateStartPoint,
} from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { assessEyebrow } from "@/foundation/ui/b2bTokens";
import { boardChip, boardInput, boardLabel, boardTile } from "@/foundation/ui/boardKit";

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

  return (
    <label className={`${boardTile} block cursor-pointer ${selected ? "border-osce-accent" : ""}`}>
      <input
        type="radio"
        name="station-template-start"
        checked={selected}
        onChange={onSelect}
        aria-label={`${option.title}. ${option.description}. ${sectionCount} sections.`}
        className="mb-1 mr-1 h-3.5 w-3.5 accent-osce-accent"
      />
      <b className="mt-1 block text-assess-h2 font-semibold text-ink">{option.title}</b>
      {option.recommended ? <span className={boardChip("info")}>Recommended</span> : null}
      <div className="text-assess-meta text-ink-muted">
        {option.description} · {sectionCount} {sectionCount === 1 ? "section" : "sections"}
      </div>
    </label>
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
      <p className={[assessEyebrow, "mb-3.5"].join(" ")}>{sectionLabel}</p>
      <div
        role="radiogroup"
        aria-label={sectionLabel}
        className="grid w-full grid-cols-1 gap-3 min-[901px]:grid-cols-3"
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
    <div>
      <label htmlFor="b2b-template-start-title" className={boardLabel}>
        Template title
      </label>
      <input
        id="b2b-template-start-title"
        value={title}
        onChange={(e) => onTitleChange(e.target.value)}
        className={boardInput}
        placeholder="Untitled template"
        autoComplete="off"
      />
    </div>
  );

  return (
    <>
      {examField ? (
        <div className="flex flex-wrap gap-4 [&>div]:min-w-[200px] [&>div]:flex-1">
          {examField}
          {titleField}
        </div>
      ) : (
        titleField
      )}
      {layoutHint ? (
        <p className="text-assess-meta text-ink-muted">{layoutHint}</p>
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
    </>
  );
}
