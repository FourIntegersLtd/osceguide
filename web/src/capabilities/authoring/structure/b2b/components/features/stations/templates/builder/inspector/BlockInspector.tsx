import { useAssessWords } from "@/capabilities/assess-words";
import { Checkbox, Select, Textarea } from "@/foundation/ui";
import { columnsFromLabels } from "@/capabilities/authoring/structure/b2b/lib/stations/richBlockValues";
import { newId } from "@/capabilities/authoring/structure/b2b/lib/stations/stationTemplatePresets";
import { formsOrderForKind, type TemplateKind } from "@/capabilities/authoring/structure/b2b/lib/stations/blockTypeLabels";
import { blockRole, roleMeta, rolesForAudience, sectionAudience } from "@/capabilities/authoring/structure/b2b/lib/stations/blockRoles";
import { splitMultilineToTrimmedLinesKeepEmpty } from "@/capabilities/authoring/structure/b2b/lib/string/splitMultilineToTrimmedLines";
import type {
  StationBlock,
  StationBlockRole,
  StationBlockType,
  StationSection,
} from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { boardBtn, boardInput, boardButtonSmall } from "@/foundation/ui/boardKit";
import {
  inspectorHint,
  inspectorLabel,
  inspectorSelect,
} from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/inspector/MoreOptions";


function generationGuideInField(block: StationBlock, catalogHint: string): string {
  if (block.generationHint !== undefined && block.generationHint !== "") {
    return block.generationHint;
  }
  return catalogHint;
}

/** Save edits on the template; empty or matching the exam model clears the override. */
function patchGenerationGuide(
  onPatch: (patch: Partial<StationBlock>) => void,
  catalogHint: string,
  nextRaw: string,
) {
  const next = nextRaw.trim();
  if (!catalogHint) {
    onPatch({ generationHint: nextRaw });
    return;
  }
  if (!next || next === catalogHint.trim()) {
    onPatch({ generationHint: "" });
    return;
  }
  onPatch({ generationHint: nextRaw });
}

export function BlockInspector({
  kind,
  block,
  section,
  onPatch,
  onChangeType,
  onDuplicate,
  onRemove,
  blockHints,
  profileGuidesLoading,
}: {
  kind: TemplateKind;
  block: StationBlock;
  section: StationSection;
  blockHints?: Record<string, string>;
  profileGuidesLoading?: boolean;
  onPatch: (patch: Partial<StationBlock>) => void;
  onChangeType: (type: StationBlockType) => void;
  onDuplicate: () => void;
  onRemove: () => void;
}) {
  const w = useAssessWords();
  const audience = sectionAudience(section);
  const role = blockRole(block, section);
  const roleOptions = rolesForAudience(audience, w);
  const roleIsChoice = kind === "station" && roleOptions.length > 1;

  const catalogHint = blockHints?.[block.id] ?? "";

  return (
    <>
      <div>
        <label htmlFor="block-inspector-label" className={inspectorLabel}>Label</label>
        <input
          id="block-inspector-label"
          value={block.label}
          onChange={(e) => onPatch({ label: e.target.value })}
          className={boardInput}
          placeholder="What the author fills in"
        />
      </div>
      <div>
        <label htmlFor="block-inspector-answer-format" className={inspectorLabel}>Answer format</label>
        <Select
          id="block-inspector-answer-format"
          className={inspectorSelect}
          value={block.type}
          onChange={(e) => onChangeType(e.target.value as StationBlockType)}
        >
          {formsOrderForKind(kind).map((m) => (
            <option key={m.type} value={m.type}>
              {m.formsLabel}
            </option>
          ))}
        </Select>
      </div>
      {kind === "station" ? (
        <div>
          {/* A label only while there is a control; the fixed role is text. */}
          {roleIsChoice ? (
            <label htmlFor="block-inspector-role" className={inspectorLabel}>
              Used in the station as
            </label>
          ) : (
            <p className={inspectorLabel}>Used in the station as</p>
          )}
          {roleIsChoice ? (
            <Select
              id="block-inspector-role"
              className={inspectorSelect}
              value={role}
              onChange={(e) => onPatch({ role: e.target.value as StationBlockRole })}
            >
              {roleOptions.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.label}
                </option>
              ))}
            </Select>
          ) : (
            <p className="rounded-osce-md bg-osce-canvas px-3 py-2 text-assess-label text-ink-muted">
              {roleMeta(role, w).label}
            </p>
          )}
          <p className={inspectorHint}>{roleMeta(role, w).description}</p>
        </div>
      ) : null}
      <Checkbox
        label="Required"
        description="Authors must fill this in"
        checked={!!block.required}
        onChange={(e) => onPatch({ required: e.target.checked })}
      />

      {(block.type === "singleSelect" || block.type === "multiSelect") && (
        <div>
          <label htmlFor="block-inspector-options-one-per-line" className={inspectorLabel}>Options (one per line)</label>
          <Textarea
            id="block-inspector-options-one-per-line"
            value={block.options.join("\n")}
            onChange={(e) =>
              onPatch({
                options: splitMultilineToTrimmedLinesKeepEmpty(e.target.value),
              } as Partial<StationBlock>)
            }
            rows={4}
          />
        </div>
      )}
      {block.type === "checklist" && (
        <div>
          <label htmlFor="block-inspector-items-one-per-line" className={inspectorLabel}>Items (one per line)</label>
          <Textarea
            id="block-inspector-items-one-per-line"
            value={block.items.map((it) => it.label).join("\n")}
            onChange={(e) => {
              const labels = splitMultilineToTrimmedLinesKeepEmpty(
                e.target.value,
              );
              onPatch({
                items: labels.map((l, i) => ({
                  id: block.items[i]?.id ?? newId("item"),
                  label: l,
                })),
              } as Partial<StationBlock>);
            }}
            rows={4}
          />
        </div>
      )}
      {block.type === "records" && (
        <div>
          <label htmlFor="block-inspector-columns" className={inspectorLabel}>Columns (one per line)</label>
          <Textarea
            id="block-inspector-columns"
            value={(block.fields ?? []).map((field) => field.label).join("\n")}
            onChange={(e) =>
              onPatch({
                fields: columnsFromLabels(splitMultilineToTrimmedLinesKeepEmpty(e.target.value), block.fields ?? []),
              } as Partial<StationBlock>)
            }
            rows={5}
          />
          <p className={inspectorHint}>
            Each record shows these, in this order. Renaming a column keeps the values already written under it.
          </p>
        </div>
      )}
      {block.type === "scale" && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="block-inspector-min" className={inspectorLabel}>Min</label>
            <input
              id="block-inspector-min"
              type="number"
              value={block.min}
              onChange={(e) =>
                onPatch({ min: Number(e.target.value) } as Partial<StationBlock>)
              }
              className={boardInput}
            />
          </div>
          <div>
            <label htmlFor="block-inspector-max" className={inspectorLabel}>Max</label>
            <input
              id="block-inspector-max"
              type="number"
              value={block.max}
              onChange={(e) =>
                onPatch({ max: Number(e.target.value) } as Partial<StationBlock>)
              }
              className={boardInput}
            />
          </div>
        </div>
      )}
      {block.type === "ragCriterion" && (
        <div>
          <label htmlFor="block-inspector-feedback-scoring-path" className={inspectorLabel}>Feedback scoring path</label>
          <input
            id="block-inspector-feedback-scoring-path"
            value={block.pathStem}
            onChange={(e) => onPatch({ pathStem: e.target.value })}
            className={boardInput}
            placeholder="e.g. global_skills.structures_consultation"
          />
          <p className={inspectorHint}>
            Links this marking row to the score and comments saved in feedback.
          </p>
        </div>
      )}

      {kind === "station" ? (
        <div>
          <label htmlFor="block-inspector-generate-draft-instructions" className={inspectorLabel}>Generate draft instructions</label>
          {profileGuidesLoading ? (
            <p className={inspectorHint}>Loading exam model instructions…</p>
          ) : (
            <>
              <Textarea
                id="block-inspector-generate-draft-instructions"
                value={generationGuideInField(block, catalogHint)}
                onChange={(e) =>
                  patchGenerationGuide(onPatch, catalogHint.trim(), e.target.value)
                }
                className="min-h-24"
                rows={4}
                placeholder={
                  catalogHint
                    ? undefined
                    : "Tell the AI what to write in this field when someone clicks Generate draft"
                }
              />
              {!catalogHint ? (
                <p className={inspectorHint}>
                  This field is not in the exam catalog (common for blank templates and new
                  fields). Add your own instructions here. They are saved on the template.
                </p>
              ) : (
                <p className={inspectorHint}>
                  Starts from the exam model. Edit here to change it for this template only.
                </p>
              )}
            </>
          )}
        </div>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <button type="button" className={boardButtonSmall} onClick={onDuplicate}>
          Duplicate
        </button>
        <button type="button" className={boardBtn("danger", true)} onClick={onRemove}>
          Delete field
        </button>
      </div>
    </>
  );
}
