/** Minimal station / feedback structure shape used by the visual editors. */

export type BlockType =
  | "list"
  | "shortText"
  | "longText"
  | "singleSelect"
  | "ragCriterion";

export interface StationBlock {
  id: string;
  type: BlockType;
  label: string;
  required?: boolean;
  placeholder?: string;
  options?: string[];
  itemLabel?: string;
  pathStem?: string;
}

export interface StationSection {
  id: string;
  title: string;
  blocks: StationBlock[];
}

export interface StationStructure {
  schemaVersion: number;
  sections: StationSection[];
}

export function newStructureId(prefix: string): string {
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

export function blankStructure(): StationStructure {
  return {
    schemaVersion: 1,
    sections: [
      {
        id: newStructureId("sec"),
        title: "Section",
        blocks: [{ id: newStructureId("blk"), type: "list", label: "List", itemLabel: "Item" }],
      },
    ],
  };
}

export function parseStructure(value: unknown): StationStructure | null {
  if (!value || typeof value !== "object") return null;
  const record = value as StationStructure;
  if (!Array.isArray(record.sections)) return null;
  return record;
}

export function structureFromJson(text: string): StationStructure | null {
  try {
    return parseStructure(JSON.parse(text) as unknown);
  } catch {
    return null;
  }
}
