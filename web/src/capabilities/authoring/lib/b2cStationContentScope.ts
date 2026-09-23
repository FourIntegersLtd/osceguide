import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { validateStationContent } from "@/capabilities/authoring/structure/b2b/lib/stations/validateStationContent";

/** Firestore-shaped station JSON nests fields; the B2C admin editor reads per section. */

const NESTED_SECTION_IDS = new Set([
  "patient_information",
  "doctor_information",
  "management_plan",
]);

export function contentSliceForSection(
  content: Record<string, unknown>,
  sectionId: string,
): Record<string, unknown> {
  if (!NESTED_SECTION_IDS.has(sectionId)) {
    return content;
  }
  const nested = content[sectionId];
  if (nested && typeof nested === "object" && !Array.isArray(nested)) {
    return nested as Record<string, unknown>;
  }
  return {};
}

export function mergeSectionIntoContent(
  content: Record<string, unknown>,
  sectionId: string,
  slice: Record<string, unknown>,
): Record<string, unknown> {
  if (NESTED_SECTION_IDS.has(sectionId)) {
    return { ...content, [sectionId]: slice };
  }
  return { ...content, ...slice };
}

/** Validates each accordion section against its slice (nested B2C JSON or flat template content). */
export function validateStationContentScoped(
  structure: StationStructure,
  content: Record<string, unknown>,
): { ok: true } | { ok: false; errors: string[] } {
  const errors: string[] = [];
  for (const section of structure.sections ?? []) {
    const slice = contentSliceForSection(content, section.id);
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
