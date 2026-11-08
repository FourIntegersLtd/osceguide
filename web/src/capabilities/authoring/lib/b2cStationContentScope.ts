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

/** The server's `_is_empty` (`stations/domain_audience.py`): only null, blank text and empty lists or objects are unwritten. */
function isWritten(value: unknown): boolean {
  if (value === null || value === undefined) return false;
  if (typeof value === "string") return value.trim() !== "";
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === "object") return Object.keys(value).length > 0;
  return true;
}

/** Roles `domain_audience._visible` holds off the candidate (`_ROLE_AUDIENCE` plus `_HIDDEN_ROLE`), wherever the block is filed. */
const NOT_CANDIDATE_ROLES = new Set(["examiner", "faculty", "debrief", "hidden"]);

/**
 * One block's stored value as platform-api's `content_for_template` reads it: a section whose id holds a
 * mapping (any id, not just the b2c ones) is opened for the block's own id or its id without the section's
 * prefix, and a block not found there falls back to the top-level `content[block_id]`.
 * (The server drops only the section ids it opened; here that is this section's id.)
 */
function templateValue(content: Record<string, unknown>, section: SectionRef, blockId: string): unknown {
  const nested = content[section.id];
  if (nested && typeof nested === "object" && !Array.isArray(nested)) {
    const fields = nested as Record<string, unknown>;
    const bare = blockId.replace(new RegExp(`^${section.id.split("_")[0]}_`), "");
    if (blockId in fields) return fields[blockId];
    if (bare in fields) return fields[bare];
  }
  return blockId === section.id ? undefined : content[blockId];
}

/** Whether the section holds something the candidate would read: the server's `sections_for` rule, so a blank section is told from a filled one. */
export function sectionHasContent(content: Record<string, unknown>, section: SectionRef): boolean {
  return section.blocks.some(
    (block) => !NOT_CANDIDATE_ROLES.has(block.role ?? "") && isWritten(templateValue(content, section, block.id)),
  );
}

/** The first section filed as candidate (explicitly, as the server decides) with something written, or null so the flat reading brief is still the candidate's. */
export function filledCandidateSection(
  sections: readonly StationSection[],
  content: Record<string, unknown>,
): StationSection | null {
  return sections.find((section) => section.audience === "candidate" && sectionHasContent(content, section)) ?? null;
}
