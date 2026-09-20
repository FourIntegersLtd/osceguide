"use client";

import { Button, getInputClassName } from "@/foundation/ui";
import { AuthoringButton } from "@/capabilities/authoring/parts/AuthoringButton";
import {
  blankStructure,
  newStructureId,
  type BlockType,
  type StationBlock,
  type StationStructure,
} from "@/capabilities/authoring/parts/structureTypes";

const BLOCK_TYPES: { value: BlockType; label: string }[] = [
  { value: "list", label: "List" },
  { value: "shortText", label: "Short text" },
  { value: "longText", label: "Long text" },
  { value: "singleSelect", label: "Single select" },
  { value: "ragCriterion", label: "RAG criterion" },
];

export function StructureBuilder({
  value,
  onChange,
}: {
  value: StationStructure;
  onChange: (next: StationStructure) => void;
}) {
  const updateSection = (index: number, patch: Partial<StationStructure["sections"][0]>) => {
    const sections = value.sections.map((section, i) =>
      i === index ? { ...section, ...patch } : section,
    );
    onChange({ ...value, sections });
  };

  const updateBlock = (sectionIndex: number, blockIndex: number, patch: Partial<StationBlock>) => {
    const sections = value.sections.map((section, si) => {
      if (si !== sectionIndex) return section;
      const blocks = section.blocks.map((block, bi) =>
        bi === blockIndex ? { ...block, ...patch } : block,
      );
      return { ...section, blocks };
    });
    onChange({ ...value, sections });
  };

  return (
    <div className="flex flex-col gap-4">
      {value.sections.map((section, sectionIndex) => (
        <div
          key={section.id}
          className="rounded-lg border border-b2b-border bg-white p-4 shadow-sm"
        >
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <input
              value={section.title}
              onChange={(e) => updateSection(sectionIndex, { title: e.target.value })}
              className={`min-w-[12rem] flex-1 ${getInputClassName()}`}
              placeholder="Section title"
            />
            <AuthoringButton
              variant="secondary"
              size="xs"
              onClick={() => {
                const sections = value.sections.filter((_, i) => i !== sectionIndex);
                onChange({ ...value, sections: sections.length ? sections : blankStructure().sections });
              }}
            >
              Remove section
            </AuthoringButton>
          </div>

          <ul className="flex flex-col gap-3">
            {section.blocks.map((block, blockIndex) => (
              <li
                key={block.id}
                className="grid gap-2 rounded-md border border-b2b-border/60 bg-b2b-surface/40 p-3 sm:grid-cols-2"
              >
                <input
                  value={block.label}
                  onChange={(e) => updateBlock(sectionIndex, blockIndex, { label: e.target.value })}
                  className={getInputClassName()}
                  placeholder="Field label"
                />
                <select
                  value={block.type}
                  onChange={(e) =>
                    updateBlock(sectionIndex, blockIndex, {
                      type: e.target.value as BlockType,
                    })
                  }
                  className={getInputClassName()}
                >
                  {BLOCK_TYPES.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                {block.type === "singleSelect" ? (
                  <input
                    value={(block.options ?? []).join(", ")}
                    onChange={(e) =>
                      updateBlock(sectionIndex, blockIndex, {
                        options: e.target.value
                          .split(",")
                          .map((s) => s.trim())
                          .filter(Boolean),
                      })
                    }
                    className={`sm:col-span-2 ${getInputClassName()}`}
                    placeholder="Options, comma-separated"
                  />
                ) : null}
                {block.type === "ragCriterion" ? (
                  <input
                    value={block.pathStem ?? ""}
                    onChange={(e) => updateBlock(sectionIndex, blockIndex, { pathStem: e.target.value })}
                    className={`sm:col-span-2 ${getInputClassName()}`}
                    placeholder="Path stem (e.g. global_skills.structures_consultation)"
                  />
                ) : null}
                <div className="flex items-center justify-end sm:col-span-2">
                  <AuthoringButton
                    variant="ghost"
                    size="xs"
                    onClick={() => {
                      const blocks = section.blocks.filter((_, i) => i !== blockIndex);
                      updateSection(sectionIndex, { blocks });
                    }}
                  >
                    Remove field
                  </AuthoringButton>
                </div>
              </li>
            ))}
          </ul>

          <AuthoringButton
            variant="secondary"
            size="xs"
            className="mt-3"
            onClick={() => {
              const block: StationBlock = {
                id: newStructureId("blk"),
                type: "list",
                label: "New field",
                itemLabel: "Item",
              };
              updateSection(sectionIndex, { blocks: [...section.blocks, block] });
            }}
          >
            Add field
          </AuthoringButton>
        </div>
      ))}

      <AuthoringButton
        variant="secondary"
        size="sm"
        onClick={() =>
          onChange({
            ...value,
            sections: [
              ...value.sections,
              {
                id: newStructureId("sec"),
                title: "New section",
                blocks: [{ id: newStructureId("blk"), type: "list", label: "List", itemLabel: "Item" }],
              },
            ],
          })
        }
      >
        Add section
      </AuthoringButton>
    </div>
  );
}
