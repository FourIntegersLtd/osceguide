import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";

/** B2B-style feedback templates stored on platform-api (see rubrics service validation). */
export const STRUCTURE_FEEDBACK_TEMPLATE_KIND = "structure" as const;

export function structureFeedbackFieldSelection(
  structure: StationStructure,
): Record<string, unknown> {
  return {
    templateKind: STRUCTURE_FEEDBACK_TEMPLATE_KIND,
    structure,
  };
}

export function structureFromFeedbackFieldSelection(
  fieldSelection: unknown,
): StationStructure | null {
  if (!fieldSelection || typeof fieldSelection !== "object") return null;
  const record = fieldSelection as Record<string, unknown>;
  if (record.templateKind !== STRUCTURE_FEEDBACK_TEMPLATE_KIND) return null;
  const structure = record.structure;
  if (!structure || typeof structure !== "object") return null;
  return structure as StationStructure;
}
