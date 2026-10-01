import { newId } from "@/capabilities/authoring/structure/b2b/lib/stations/stationTemplatePresets";
import { audienceMeta, sectionAudience } from "@/capabilities/authoring/structure/b2b/lib/stations/blockRoles";
import type {
  StationBlock,
  StationBlockRole,
  StationBlockType,
  StationSection,
  StationSectionAudience,
  StationStructure,
} from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";

export function defaultBlock(type: StationBlockType): StationBlock {
  const id = newId("blk");
  const label = "Untitled field";
  switch (type) {
    case "shortText":
      return { id, type: "shortText", label };
    case "longText":
      return { id, type: "longText", label };
    case "list":
      return { id, type: "list", label, itemLabel: "Item" };
    case "media":
      return { id, type: "media", label };
    case "records":
      return {
        id,
        type: "records",
        label,
        fields: [
          { key: "name", label: "Name" },
          { key: "details", label: "Details" },
        ],
      };
    case "qaList":
      return { id, type: "qaList", label };
    case "groupedList":
      return { id, type: "groupedList", label };
    case "singleSelect":
      return {
        id,
        type: "singleSelect",
        label,
        options: ["Option 1", "Option 2", "Option 3"],
      };
    case "multiSelect":
      return {
        id,
        type: "multiSelect",
        label,
        options: ["Option 1", "Option 2", "Option 3"],
      };
    case "checklist":
      return {
        id,
        type: "checklist",
        label,
        items: [
          { id: newId("item"), label: "Item 1" },
          { id: newId("item"), label: "Item 2" },
          { id: newId("item"), label: "Item 3" },
        ],
      };
    case "scale":
      return {
        id,
        type: "scale",
        label,
        min: 1,
        max: 5,
        labels: { "1": "Poor", "3": "OK", "5": "Excellent" },
      };
    case "ragCriterion":
      return {
        id,
        type: "ragCriterion",
        label,
        pathStem: "global_skills.example_skill",
      };
    default: {
      const _exhaustive: never = type;
      return _exhaustive;
    }
  }
}

export function createSection(
  title = "New section",
  audience: StationSectionAudience = "patient",
): StationSection {
  return {
    id: newId("sec"),
    title,
    audience,
    blocks: [
      {
        id: newId("blk"),
        type: "longText",
        label: "Content",
        role: audienceMeta(audience).defaultRole,
      },
    ],
  };
}

export function addSection(
  structure: StationStructure,
  audience?: StationSectionAudience,
): StationStructure {
  // A new section follows the audience of the one before it, so authoring the
  // examiner's notes does not keep producing patient sections.
  const last = structure.sections.at(-1);
  const section = createSection(
    "New section",
    audience ?? (last ? sectionAudience(last) : "patient"),
  );
  return { ...structure, sections: [...structure.sections, section] };
}

/** Change who a section is for; blocks whose role no longer fits follow it. */
export function setSectionAudience(
  structure: StationStructure,
  sectionId: string,
  audience: StationSectionAudience,
): StationStructure {
  const fallback = audienceMeta(audience).defaultRole;
  return {
    ...structure,
    sections: structure.sections.map((s) => {
      if (s.id !== sectionId) return s;
      return {
        ...s,
        audience,
        blocks: s.blocks.map((b) => {
          const keep = b.role && ROLE_AUDIENCE[b.role] === audience;
          return { ...b, role: keep ? b.role : fallback } as StationBlock;
        }),
      };
    }),
  };
}

const ROLE_AUDIENCE: Record<StationBlockRole, StationSectionAudience> = {
  persona: "patient",
  complaint: "patient",
  history: "patient",
  medications: "patient",
  social: "patient",
  examination: "patient",
  instructions: "patient",
  hidden: "patient",
  candidate_brief: "candidate",
  examiner: "examiner",
  faculty: "faculty",
};

export function removeSection(
  structure: StationStructure,
  sectionId: string,
): StationStructure {
  return {
    ...structure,
    sections: structure.sections.filter((s) => s.id !== sectionId),
  };
}

export function updateSection(
  structure: StationStructure,
  sectionId: string,
  patch: Partial<StationSection>,
): StationStructure {
  return {
    ...structure,
    sections: structure.sections.map((s) =>
      s.id === sectionId ? { ...s, ...patch } : s,
    ),
  };
}

export function reorderSections(
  structure: StationStructure,
  fromIndex: number,
  toIndex: number,
): StationStructure {
  if (
    fromIndex === toIndex ||
    fromIndex < 0 ||
    toIndex < 0 ||
    fromIndex >= structure.sections.length ||
    toIndex >= structure.sections.length
  ) {
    return structure;
  }
  const next = [...structure.sections];
  const [item] = next.splice(fromIndex, 1);
  if (!item) return structure;
  next.splice(toIndex, 0, item);
  return { ...structure, sections: next };
}

export function addBlock(
  structure: StationStructure,
  sectionId: string,
  type: StationBlockType,
  index?: number,
): StationStructure {
  return {
    ...structure,
    sections: structure.sections.map((s) => {
      if (s.id !== sectionId) return s;
      const block: StationBlock = {
        ...defaultBlock(type),
        role: audienceMeta(sectionAudience(s)).defaultRole,
      };
      const blocks = [...s.blocks];
      if (index === undefined || index >= blocks.length) {
        blocks.push(block);
      } else {
        blocks.splice(Math.max(0, index), 0, block);
      }
      return { ...s, blocks };
    }),
  };
}

export function removeBlock(
  structure: StationStructure,
  sectionId: string,
  blockId: string,
): StationStructure {
  return {
    ...structure,
    sections: structure.sections.map((s) =>
      s.id === sectionId
        ? { ...s, blocks: s.blocks.filter((b) => b.id !== blockId) }
        : s,
    ),
  };
}

export function updateBlock(
  structure: StationStructure,
  sectionId: string,
  blockId: string,
  patch: Partial<StationBlock>,
): StationStructure {
  return {
    ...structure,
    sections: structure.sections.map((s) =>
      s.id !== sectionId
        ? s
        : {
            ...s,
            blocks: s.blocks.map((b) =>
              b.id === blockId ? ({ ...b, ...patch } as StationBlock) : b,
            ),
          },
    ),
  };
}

export function changeBlockType(
  structure: StationStructure,
  sectionId: string,
  blockId: string,
  nextType: StationBlockType,
): StationStructure {
  const sec = structure.sections.find((s) => s.id === sectionId);
  const prev = sec?.blocks.find((b) => b.id === blockId);
  if (!prev || prev.type === nextType) return structure;

  const fresh = defaultBlock(nextType);
  let nextBlock: StationBlock = {
    ...fresh,
    id: prev.id,
    label: prev.label,
    required: prev.required,
    ...(prev.role ? { role: prev.role } : {}),
  };
  if (
    (nextType === "shortText" ||
      nextType === "longText" ||
      nextType === "list") &&
    typeof prev.placeholder === "string" &&
    prev.placeholder.trim()
  ) {
    nextBlock = { ...nextBlock, placeholder: prev.placeholder };
  }

  return updateBlock(structure, sectionId, blockId, nextBlock);
}

export function duplicateBlock(
  structure: StationStructure,
  sectionId: string,
  blockId: string,
): StationStructure {
  const sec = structure.sections.find((s) => s.id === sectionId);
  if (!sec) return structure;
  const idx = sec.blocks.findIndex((b) => b.id === blockId);
  if (idx < 0) return structure;

  const blk = sec.blocks[idx];
  const raw = JSON.parse(JSON.stringify(blk)) as StationBlock & {
    items?: Array<{ id: string; label: string }>;
  };
  raw.id = newId("blk");
  if (raw.type === "checklist" && Array.isArray(raw.items)) {
    raw.items = raw.items.map((it) => ({ ...it, id: newId("item") }));
  }

  return {
    ...structure,
    sections: structure.sections.map((s) => {
      if (s.id !== sectionId) return s;
      const blocks = [
        ...s.blocks.slice(0, idx + 1),
        raw as StationBlock,
        ...s.blocks.slice(idx + 1),
      ];
      return { ...s, blocks };
    }),
  };
}

export function moveBlockWithinSection(
  structure: StationStructure,
  sectionId: string,
  fromIndex: number,
  toIndex: number,
): StationStructure {
  const sec = structure.sections.find((s) => s.id === sectionId);
  if (!sec) return structure;
  if (
    fromIndex === toIndex ||
    fromIndex < 0 ||
    toIndex < 0 ||
    fromIndex >= sec.blocks.length ||
    toIndex >= sec.blocks.length
  ) {
    return structure;
  }
  const blocks = [...sec.blocks];
  const [item] = blocks.splice(fromIndex, 1);
  if (!item) return structure;
  blocks.splice(toIndex, 0, item);
  return updateSection(structure, sectionId, { blocks });
}

export function moveBlockAcrossSections(
  structure: StationStructure,
  fromSectionId: string,
  blockId: string,
  toSectionId: string,
  toIndex: number,
): StationStructure {
  const fromSection = structure.sections.find((s) => s.id === fromSectionId);
  if (!fromSection) return structure;
  const fromIndex = fromSection.blocks.findIndex((b) => b.id === blockId);
  if (fromIndex < 0) return structure;

  const block = fromSection.blocks[fromIndex];
  if (!block) return structure;
  let next = updateSection(structure, fromSectionId, {
    blocks: fromSection.blocks.filter((b) => b.id !== blockId),
  });

  const toSection = next.sections.find((s) => s.id === toSectionId);
  if (!toSection) return structure;
  const blocks = [...toSection.blocks];
  const insertAt = Math.max(0, Math.min(toIndex, blocks.length));
  blocks.splice(insertAt, 0, block);
  next = updateSection(next, toSectionId, { blocks });
  return next;
}

export function countFields(structure: StationStructure): number {
  return structure.sections.reduce(
    (acc, s) => acc + (s.blocks?.length || 0),
    0,
  );
}

export function findBlockLocation(
  structure: StationStructure,
  blockId: string,
): { sectionId: string; blockIndex: number } | null {
  for (const section of structure.sections) {
    const blockIndex = section.blocks.findIndex((b) => b.id === blockId);
    if (blockIndex >= 0) {
      return { sectionId: section.id, blockIndex };
    }
  }
  return null;
}

export type BuilderSelection =
  | { kind: "none" }
  | { kind: "section"; sectionId: string }
  | { kind: "block"; sectionId: string; blockId: string };

export const SECTION_DRAG_PREFIX = "section:";
export const BLOCK_DRAG_PREFIX = "block:";

export function parseDragId(id: string): {
  kind: "section" | "block";
  value: string;
  sectionId?: string;
  blockId?: string;
} | null {
  if (id.startsWith(SECTION_DRAG_PREFIX)) {
    return { kind: "section", value: id.slice(SECTION_DRAG_PREFIX.length) };
  }
  if (id.startsWith(BLOCK_DRAG_PREFIX)) {
    const rest = id.slice(BLOCK_DRAG_PREFIX.length);
    const [sectionId, blockId] = rest.split(":");
    if (!sectionId || !blockId) return null;
    return { kind: "block", value: rest, sectionId, blockId };
  }
  return null;
}

export function sectionDragId(sectionId: string): string {
  return `${SECTION_DRAG_PREFIX}${sectionId}`;
}

export function blockDragId(sectionId: string, blockId: string): string {
  return `${BLOCK_DRAG_PREFIX}${sectionId}:${blockId}`;
}
