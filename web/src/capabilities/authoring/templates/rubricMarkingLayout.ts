import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";

export function emptyMarkingLayout(): StationStructure {
  return { schemaVersion: 1, sections: [] };
}

export function markingLayoutFromVersion(raw: unknown): StationStructure | null {
  if (!raw || typeof raw !== "object") return null;
  const record = raw as Record<string, unknown>;
  if (!Array.isArray(record.sections)) return null;
  return raw as StationStructure;
}

export function markingLayoutToJson(structure: StationStructure): Record<string, unknown> {
  return structure as unknown as Record<string, unknown>;
}
