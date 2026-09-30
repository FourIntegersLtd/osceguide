"use client";

import type { MediaUploads } from "@/capabilities/authoring/structure/b2b/components/features/stations/pages/MediaBlockEditor";
import { StationInstanceBlocks } from "@/capabilities/authoring/structure/b2b/components/features/stations/pages/StationInstanceBlocks";
import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import {
  contentSliceForSection,
  mergeSectionIntoContent,
} from "@/capabilities/authoring/lib/b2cStationContentScope";
import { Dropdown } from "@/foundation/table";

/** Template-shaped station content — B2C admin-style sections + list fields. */
export function StationInstanceContentPanel({
  structure,
  content,
  onChange,
  readOnly,
  media,
}: {
  structure: StationStructure;
  content: Record<string, unknown>;
  onChange: (next: Record<string, unknown>) => void;
  readOnly?: boolean;
  media?: MediaUploads;
}) {
  return (
    <div className="space-y-3">
      {structure.sections.map((sec, sectionIndex) => (
        <Dropdown
          key={sec.id}
          title={sec.title}
          className="mt-0"
          defaultOpen={sectionIndex === 0}
        >
          {sec.description ? (
            <p className="mb-4 text-osce-body text-b2c-text-muted">{sec.description}</p>
          ) : null}
          <StationInstanceBlocks
            blocks={sec.blocks}
            content={contentSliceForSection(content, sec)}
            onChange={(slice) => onChange(mergeSectionIntoContent(content, sec, slice))}
            readOnly={readOnly}
            listEditor="admin"
            media={media}
          />
        </Dropdown>
      ))}
    </div>
  );
}
