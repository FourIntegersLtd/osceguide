import type { StationSection, StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { validateStationContent } from "@/capabilities/authoring/structure/b2b/lib/stations/validateStationContent";

/** Firestore-shaped station JSON nests fields; the B2C admin editor reads per section. */

const NESTED_SECTION_IDS = new Set([
  "patient_information",
  "doctor_information",
  "management_plan",
]);

type SectionRef = Pick<StationSection, "id" | "blocks">;

/** The section's own object when the station stores it nested (b2c); null when it is stored flat. */
function nestedOf(content: Record<string, unknown>, sectionId: string): Record<string, unknown> | null {
  if (!NESTED_SECTION_IDS.has(sectionId)) return null;
  const nested = content[sectionId];
  return nested && typeof nested === "object" && !Array.isArray(nested) ? (nested as Record<string, unknown>) : null;
}

/**
 * The key a block's value is stored under in a nested section: its own id, or
 * its id without the section's prefix (`doctor_photos` is
 * `doctor_information.photos`). Mirrors platform-api's `content_for_template`.
 */
function storedKey(nested: Record<string, unknown>, sectionId: string, blockId: string): string {
  const prefix = `${sectionId.split("_")[0]}_`;
  const bare = blockId.startsWith(prefix) ? blockId.slice(prefix.length) : blockId;
  return blockId in nested || !(bare in nested) ? blockId : bare;
}

/** A section's values keyed by block id, whether the station stores them nested (b2c) or flat. */
export function contentSliceForSection(
  content: Record<string, unknown>,
  section: SectionRef,
): Record<string, unknown> {
  const nested = nestedOf(content, section.id);
  if (!nested) {
    return content;
  }
  const slice = { ...nested };
  for (const block of section.blocks) {
    const key = storedKey(nested, section.id, block.id);
    if (key !== block.id) slice[block.id] = nested[key];
  }
  return slice;
}

/** Writes a section's edited slice back where each value was read from. */
export function mergeSectionIntoContent(
  content: Record<string, unknown>,
  section: SectionRef,
  slice: Record<string, unknown>,
): Record<string, unknown> {
  const nested = nestedOf(content, section.id);
  if (!nested) {
    return { ...content, ...slice };
  }
  const merged = { ...slice };
  for (const block of section.blocks) {
    const key = storedKey(nested, section.id, block.id);
    if (key !== block.id && block.id in merged) {
      merged[key] = merged[block.id];
      delete merged[block.id];
    }
  }
  return { ...content, [section.id]: merged };
}

/** Validates each accordion section against its slice (nested B2C JSON or flat template content). */
export function validateStationContentScoped(
  structure: StationStructure,
  content: Record<string, unknown>,
): { ok: true } | { ok: false; errors: string[] } {
  const errors: string[] = [];
  for (const section of structure.sections ?? []) {
    const slice = contentSliceForSection(content, section);
    const partial = validateStationContent(
      {
        schemaVersion: structure.schemaVersion,
        layout: structure.layout,
        sections: [section],
      },
      slice,
    );
    if (!partial.ok) {
      errors.push(...partial.errors);
    }
  }
  return errors.length === 0 ? { ok: true } : { ok: false, errors };
}
