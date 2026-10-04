"use client";

import type { MediaUploads } from "@/capabilities/authoring/structure/b2b/components/features/stations/pages/MediaBlockEditor";
import { StationInstanceBlocks } from "@/capabilities/authoring/structure/b2b/components/features/stations/pages/StationInstanceBlocks";
import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import {
  contentSliceForSection,
  mergeSectionIntoContent,
} from "@/capabilities/authoring/lib/b2cStationContentScope";
import { FoldSection } from "@/foundation/ui";

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
        <FoldSection
          key={sec.id}
          number={sectionIndex + 1}
          title={sec.title}
          description={sec.description || undefined}
          defaultOpen={sectionIndex === 0}
        >
          <StationInstanceBlocks
            blocks={sec.blocks}
            content={contentSliceForSection(content, sec)}
            onChange={(slice) => onChange(mergeSectionIntoContent(content, sec, slice))}
            readOnly={readOnly}
            listEditor="admin"
            media={media}
          />
        </FoldSection>
      ))}
    </div>
  );
}
