import {
  getAt,
  isJsonObject,
  listAt,
  setAt,
  updateList,
  type JsonObject,
  type JsonPath,
} from "@/capabilities/authoring/rubrics/jsonPath";
import type { FieldRole, FieldType, RatingKind, SectionKind } from "@/capabilities/authoring/rubrics/rubricVocabulary";

/**
 * The edits an author makes to a version 2 rubric structure.
 *
 * Each function takes the structure and returns a new one; nothing is mutated,
 * so React sees every change and an undo is just the previous value. These
 * are the rules the backend would otherwise refuse with a problem — a domain's
 * rating field must carry the rating's name, a pick-one needs an option — made
 * true at the moment of the edit, so an author meets fewer problems in the
 * first place. What the backend still refuses is shown next to the input by
 * `problems.ts`.
 */

export type RubricStructure = JsonObject;

/** A rubric id: lower case, starts with a letter, underscores between words, at most 64. */
export const IDENTIFIER_PATTERN = /^[a-z][a-z0-9_]{0,63}$/;

/* ---------- ids ---------- */

/** The id a label suggests: "History taking" is `history_taking`. */
export function identifierFrom(label: string, fallback = "item"): string {
  const words = label
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  const started = /^[a-z]/.test(words) ? words : `${fallback}_${words}`.replace(/_+$/, "");
  return started.slice(0, 64).replace(/_+$/, "");
}

/** `base`, or `base_2`, `base_3`… — the first one not already in `taken`. */
export function uniqueIdentifier(base: string, taken: Iterable<string>): string {
  const used = new Set(taken);
  if (!used.has(base)) return base;
  for (let suffix = 2; ; suffix += 1) {
    const candidate = `${base.slice(0, 60)}_${suffix}`;
    if (!used.has(candidate)) return candidate;
  }
}

/** Every id in a list of objects (a section's fields, a domain's competencies). */
function idsOf(items: unknown[]): string[] {
  return items.flatMap((item) => (isJsonObject(item) && typeof item.id === "string" ? [item.id] : []));
}

/** Top-level ids: a section's own id, or a lone field section's field id. */
function topLevelIds(structure: RubricStructure): string[] {
  return listAt(structure, ["sections"]).flatMap((section) => {
    if (!isJsonObject(section)) return [];
    if (section.kind === "field") return isJsonObject(section.field) ? idsOf([section.field]) : [];
    return idsOf([section]);
  });
}

/* ---------- the rating ---------- */

export interface RatingDraft {
  kind: RatingKind | null;
  field: string;
  scale: string[];
  minimum: number | null;
  maximum: number | null;
  step: "number" | "integer";
}

const RAG_SCALE = ["G", "A", "R"];

/** The rating as the forms read it, with the backend's defaults filled in. */
export function readRating(structure: RubricStructure): RatingDraft {
  const raw = isJsonObject(structure.rating) ? structure.rating : {};
  const kind = raw.kind === "rag" || raw.kind === "scale" || raw.kind === "range" || raw.kind === "boolean" ? raw.kind : null;
  const scale = Array.isArray(raw.scale) ? raw.scale.map(String) : kind === "rag" ? RAG_SCALE : [];
  return {
    kind,
    field: typeof raw.field === "string" ? raw.field : "score",
    scale,
    minimum: typeof raw.minimum === "number" ? raw.minimum : null,
    maximum: typeof raw.maximum === "number" ? raw.maximum : null,
    step: raw.step === "integer" ? "integer" : "number",
  };
}

/**
 * The rating switched to another kind, with that kind's starting values.
 *
 * Tones are refused on a scale ("colour comes from the grade's position"), so
 * they go when the new kind is R/A/G or a scale. Descriptors are kept only
 * where the new scale still has their grade; a range or met / not met does
 * not read descriptors at all, so they are left for a switch back.
 */
export function withRatingKind(structure: RubricStructure, kind: RatingKind): RubricStructure {
  const field = readRating(structure).field;
  const rating: JsonObject =
    kind === "rag"
      ? { kind, field }
      : kind === "scale"
        ? { kind, field, scale: ["Excellent", "Good", "Fair", "Poor"] }
        : kind === "range"
          ? { kind, field, minimum: 0, maximum: 10, step: "integer" }
          : { kind, field };
  let next = setAt(structure, ["rating"], rating);
  if (kind === "rag" || kind === "scale") {
    next = setAt(next, ["display", "tones"], undefined);
    next = pruneDescriptors(next, kind === "rag" ? RAG_SCALE : (rating.scale as string[]));
  }
  return next;
}

/** A named scale's grades replaced (best first); descriptors follow a renamed grade by position. */
export function withScale(structure: RubricStructure, scale: string[]): RubricStructure {
  const before = readRating(structure).scale;
  const renamed = new Map(before.map((grade, position) => [grade, scale[position]]));
  const withDescriptors = mapCompetencies(structure, (competency) => {
    if (!isJsonObject(competency.descriptors)) return competency;
    const descriptors: JsonObject = {};
    for (const [grade, text] of Object.entries(competency.descriptors)) {
      const target = renamed.get(grade) ?? grade;
      if (scale.includes(target)) descriptors[target] = text;
    }
    return { ...competency, descriptors };
  });
  return setAt(withDescriptors, ["rating", "scale"], scale);
}

/**
 * The rating's field renamed, everywhere it is used.
 *
 * Each domain rates its competencies in exactly one rating field, which must
 * be called what the rating says; renaming only the rating would put a
 * problem on every domain.
 */
export function withRatingField(structure: RubricStructure, field: string): RubricStructure {
  const renamed = mapSections(structure, (section) => {
    if (section.kind !== "domain") return section;
    const fields = Array.isArray(section.competencyFields) ? section.competencyFields : [];
    return {
      ...section,
      competencyFields: fields.map((spec) => (isJsonObject(spec) && spec.type === "rating" ? { ...spec, id: field } : spec)),
    };
  });
  return setAt(renamed, ["rating", "field"], field);
}

function pruneDescriptors(structure: RubricStructure, scale: readonly string[]): RubricStructure {
  return mapCompetencies(structure, (competency) => {
    if (!isJsonObject(competency.descriptors)) return competency;
    const kept = Object.entries(competency.descriptors).filter(([grade]) => scale.includes(grade));
    return { ...competency, descriptors: Object.fromEntries(kept) };
  });
}

function mapSections(structure: RubricStructure, change: (section: JsonObject) => JsonObject): RubricStructure {
  return updateList(structure, ["sections"], (sections) =>
    sections.map((section) => (isJsonObject(section) ? change(section) : section)),
  );
}

function mapCompetencies(structure: RubricStructure, change: (competency: JsonObject) => JsonObject): RubricStructure {
  return mapSections(structure, (section) => {
    if (!Array.isArray(section.competencies)) return section;
    return {
      ...section,
      competencies: section.competencies.map((competency) => (isJsonObject(competency) ? change(competency) : competency)),
    };
  });
}

/* ---------- sections, competencies and fields ---------- */

/** The role a new field of this type starts with; the author can change it. */
export function defaultRoleFor(type: FieldType): FieldRole {
  switch (type) {
    case "rating":
      return "rating";
    case "longText":
      return "explanation";
    case "list":
      return "action";
    case "singleSelect":
      return "selector";
    default:
      return "other";
  }
}

const TYPE_LABELS: Record<FieldType, string> = {
  rating: "Rating",
  shortText: "Short answer",
  longText: "Comment",
  list: "Points",
  singleSelect: "Choice",
  group: "Group",
  records: "Entries",
};

/** A new field of `type`, with an id not already used in `siblings`. */
export function newField(type: FieldType, siblings: unknown[], ratingField = "score"): JsonObject {
  const label = TYPE_LABELS[type];
  const id = type === "rating" ? ratingField : uniqueIdentifier(identifierFrom(label), idsOf(siblings));
  const field: JsonObject = { id, label, type, role: defaultRoleFor(type) };
  if (type === "singleSelect") field.options = ["Option 1"];
  if (type === "group" || type === "records") field.fields = [{ id: "detail", label: "Detail", type: "shortText", role: "other" }];
  return field;
}

/**
 * A field given another type, keeping what still applies.
 *
 * Options belong only to a pick-one and child fields only to a group or
 * records, so each is added when the new type needs it and removed when it
 * does not. The role follows the type only while it was still the old type's
 * default; one the author chose stays.
 */
export function withFieldType(field: JsonObject, type: FieldType, ratingField = "score"): JsonObject {
  const next: JsonObject = { ...field, type };
  const previousType = field.type as FieldType;
  if (field.role === undefined || field.role === defaultRoleFor(previousType)) next.role = defaultRoleFor(type);
  if (type === "rating") next.id = ratingField;
  if (type === "singleSelect") {
    if (!Array.isArray(next.options) || next.options.length === 0) next.options = ["Option 1"];
  } else delete next.options;
  if (type === "group" || type === "records") {
    if (!Array.isArray(next.fields) || next.fields.length === 0) {
      next.fields = [{ id: "detail", label: "Detail", type: "shortText", role: "other" }];
    }
  } else delete next.fields;
  if (type !== "list" && type !== "records") delete next.minItems;
  return next;
}

/** A new competency, labelled and numbered after the ones already in the domain. */
export function newCompetency(existing: unknown[]): JsonObject {
  const label = `Competency ${existing.length + 1}`;
  return { id: uniqueIdentifier(identifierFrom(label), idsOf(existing)), label, instructions: "" };
}

/** A new top-level section of `kind`, with just enough in it to be valid. */
export function newSection(structure: RubricStructure, kind: SectionKind): JsonObject {
  const taken = topLevelIds(structure);
  const count = listAt(structure, ["sections"]).length + 1;
  if (kind === "field") {
    const label = "Overall comment";
    return {
      kind,
      title: label,
      field: { id: uniqueIdentifier(identifierFrom(label), taken), label, type: "longText", role: "summary" },
    };
  }
  const title = kind === "domain" ? `Domain ${count}` : `Section ${count}`;
  const id = uniqueIdentifier(identifierFrom(title), taken);
  if (kind === "section") {
    return { id, title, kind, instructions: "", fields: [{ id: "notes", label: "Notes", type: "longText", role: "summary" }] };
  }
  const ratingField = readRating(structure).field;
  return {
    id,
    title,
    kind,
    instructions: "",
    competencies: [newCompetency([])],
    competencyFields: [
      { id: ratingField, label: "Rating", type: "rating", role: "rating" },
      { id: "evidence", label: "Evidence", type: "longText", role: "evidence" },
      { id: "explanation", label: "Explanation", type: "longText", role: "explanation" },
    ],
  };
}

/** A copy of `structure` with `item` added to the end of the list at `listPath`. */
export function appendAt(structure: RubricStructure, listPath: JsonPath, item: unknown): RubricStructure {
  return updateList(structure, listPath, (list) => [...list, item]);
}

/** The text at `path`, or "" when there is none. */
export function textAt(structure: RubricStructure, path: JsonPath): string {
  const value = getAt(structure, path);
  return typeof value === "string" ? value : "";
}
