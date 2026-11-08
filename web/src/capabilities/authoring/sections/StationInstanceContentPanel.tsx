"use client";

import type { MediaUploads } from "@/capabilities/authoring/structure/b2b/components/features/stations/pages/MediaBlockEditor";
import { StationInstanceBlocks } from "@/capabilities/authoring/structure/b2b/components/features/stations/pages/StationInstanceBlocks";
import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import {
  contentSliceForSection,
  mergeSectionIntoContent,
} from "@/capabilities/authoring/lib/b2cStationContentScope";
import { sectionAudience } from "@/capabilities/authoring/structure/b2b/lib/stations/blockRoles";
import { useAssessWords } from "@/capabilities/assess-words";
import { examinerSectionNote } from "@/capabilities/authoring/lib/authoringCopy";
import { FoldSection } from "@/foundation/ui";

/** Template-shaped station content — B2C admin-style sections + list fields. */
export function StationInstanceContentPanel({
  structure,
  content,
  onChange,
  readOnly,
  media,
  board,
  gap,
}: {
  structure: StationStructure;
  content: Record<string, unknown>;
  onChange: (next: Record<string, unknown>) => void;
  readOnly?: boolean;
  media?: MediaUploads;
  /** The institution board's folds (see FoldSection). */
  board?: boolean;
  /** Space the board's folds apart (the create screen's cards; the builder stacks them flush). */
  gap?: boolean;
}) {
  const w = useAssessWords();
  // The boards draw photos as one card under the folds, so a media block leaves its section there.
  const isMedia = (type: string) => board && type === "media";
  const sections = structure.sections
    .map((sec) => ({ sec, blocks: sec.blocks.filter((block) => !isMedia(block.type)) }))
    .filter((entry) => entry.blocks.length > 0 || !board);
  const photoSections = structure.sections.filter((sec) => sec.blocks.some((block) => isMedia(block.type)));
  const blocksFor = (sec: StationStructure["sections"][number], blocks: typeof sec.blocks) => (
    <StationInstanceBlocks
      blocks={blocks}
      content={contentSliceForSection(content, sec)}
      onChange={(slice) => onChange(mergeSectionIntoContent(content, sec, slice))}
      readOnly={readOnly}
      listEditor="admin"
      media={media}
      board={board}
    />
  );
  return (
    <div className={board ? `flex flex-col${gap ? " gap-6" : ""}` : "space-y-3"}>
      {sections.map(({ sec, blocks }, index) => {
        const note = sectionAudience(sec) === "examiner" ? examinerSectionNote(sec.title, w) : null;
        return (
        <FoldSection
          key={sec.id}
          number={index + 1}
          title={note?.title ?? sec.title}
          description={sec.description || note?.help || undefined}
          defaultOpen={index === 0}
          board={board}
        >
          {blocksFor(sec, blocks)}
        </FoldSection>
        );
      })}
      {photoSections.map((sec) => blocksFor(sec, sec.blocks.filter((block) => isMedia(block.type))))}
    </div>
  );
}
