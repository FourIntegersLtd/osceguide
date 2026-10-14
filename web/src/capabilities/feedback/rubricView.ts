import { gradeWord } from "./feedbackWords";
import {
  bandFor,
  bandName,
  formatAggregate,
  formatNumber,
  isEnumerated,
  passWord,
  ratingLabel,
  ratingTone,
  readDisplay,
  type Display,
  type MarkedResult,
  type MarkingRubric,
  type Rating,
} from "@/capabilities/feedback/rubric";

/**
 * One marked result, turned into what the feedback screen draws.
 *
 * Pure and exam-blind: it walks the rubric's sections in order and describes
 * each answer by its field's *type* (how it is shaped) and *role* (what it
 * means to the reader). `RubricFeedback.tsx` maps this onto markup and
 * nothing else, so the tests here read the same strings a person sees.
 *
 * Kept as data rather than JSX because the test runner (node:test with type
 * stripping) cannot render a component.
 */

/* ---------- the rubric's structure ---------- */

export type FieldType = "rating" | "shortText" | "longText" | "list" | "singleSelect" | "group" | "records";

/** What a field means to the reader. Anything the renderer does not know is `other`. */
export type FieldRole =
  | "rating"
  | "evidence"
  | "explanation"
  | "strength"
  | "improvement"
  | "action"
  | "flag"
  | "summary"
  | "selector"
  | "other";

export interface RubricField {
  id: string;
  label: string;
  type: FieldType;
  role: FieldRole;
  fields: RubricField[];
}

export interface RubricCompetency {
  id: string;
  label: string;
  descriptors: Record<string, string>;
}

export type RubricSection =
  | {
      kind: "domain";
      id: string;
      title: string;
      nullable: boolean;
      competencies: RubricCompetency[];
      competencyFields: RubricField[];
      fields: RubricField[];
    }
  | { kind: "section"; id: string; title: string; fields: RubricField[] }
  | { kind: "field"; field: RubricField };

type JsonObject = Record<string, unknown>;

function isObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function text(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function objects(value: unknown): JsonObject[] {
  return Array.isArray(value) ? value.filter(isObject) : [];
}

const FIELD_TYPES: readonly FieldType[] = ["rating", "shortText", "longText", "list", "singleSelect", "group", "records"];
const FIELD_ROLES: readonly FieldRole[] = [
  "rating",
  "evidence",
  "explanation",
  "strength",
  "improvement",
  "action",
  "flag",
  "summary",
  "selector",
  "other",
];

/** A field id as words, for a field an author gave no label: "missed_history" is "Missed history". */
export function humanise(identifier: string): string {
  const words = identifier.replace(/[_-]+/g, " ").trim();
  return words ? words.charAt(0).toUpperCase() + words.slice(1) : identifier;
}

function readField(raw: JsonObject): RubricField {
  const identifier = text(raw.id);
  return {
    id: identifier,
    label: text(raw.label) || humanise(identifier),
    type: FIELD_TYPES.find((type) => type === raw.type) ?? "longText",
    role: FIELD_ROLES.find((role) => role === raw.role) ?? "other",
    fields: objects(raw.fields).map(readField),
  };
}

/**
 * The sections of a rubric's structure, in the author's order.
 *
 * A `field` section is a single answer that sits at the top level of the
 * result (Ortho's station type); the API sends it as `{kind, field}`.
 */
export function readSections(structure: JsonObject): RubricSection[] {
  return objects(structure.sections).flatMap((raw): RubricSection[] => {
    if (raw.kind === "field") {
      const field = isObject(raw.field) ? raw.field : objects(raw.fields)[0];
      return field ? [{ kind: "field", field: readField(field) }] : [];
    }
    const identifier = text(raw.id);
    const title = text(raw.title) || humanise(identifier);
    const fields = objects(raw.fields).map(readField);
    if (raw.kind === "domain") {
      return [
        {
          kind: "domain",
          id: identifier,
          title,
          nullable: raw.nullable === true,
          competencies: objects(raw.competencies).map((competency) => ({
            id: text(competency.id),
            label: text(competency.label) || humanise(text(competency.id)),
            descriptors: Object.fromEntries(
              Object.entries(isObject(competency.descriptors) ? competency.descriptors : {}).filter(
                (entry): entry is [string, string] => typeof entry[1] === "string" && entry[1].trim() !== "",
              ),
            ),
          })),
          competencyFields: objects(raw.competencyFields).map(readField),
          fields,
        },
      ];
    }
    return [{ kind: "section", id: identifier, title, fields }];
  });
}

/* ---------- what the screen draws ---------- */

/** One competency's rating, drawn by rating kind. */
export interface RatingView {
  /** `grade` is a disc (rag / scale), `chip` is "x / max" (range), `check` a tick or cross (boolean). */
  shape: "grade" | "chip" | "check";
  text: string;
  tone: string | null;
  met?: boolean;
}

export type AnswerView =
  | { type: "text"; role: FieldRole; label: string; text: string }
  | { type: "tag"; role: FieldRole; label: string; text: string }
  | { type: "list"; role: FieldRole; label: string; items: string[] }
  | { type: "group"; role: FieldRole; label: string; answers: AnswerView[] }
  | { type: "records"; role: FieldRole; label: string; records: AnswerView[][] };

export interface CompetencyView {
  id: string;
  label: string;
  rating: RatingView | null;
  answers: AnswerView[];
  /** The descriptor for the best rating: what good looks like. */
  hint: string | null;
}

export interface DomainView {
  kind: "domain";
  id: string;
  title: string;
  /** The domain's value in its aggregate: "1.2/4", "67%", "2 G · 3 A · 2 R". */
  aggregate: string | null;
  passed: boolean | null;
  /** "Pass at 2/4", when the display sets a domain pass line. */
  passLine: string | null;
  competencies: CompetencyView[];
  answers: AnswerView[];
}

export interface SectionView {
  kind: "section";
  id: string;
  title: string;
  answers: AnswerView[];
}

export interface FeedbackHeader {
  /** Whose marking this is: "Your mark" for the learner, "Automatic marking" for an examiner. */
  heading: string;
  /** The station total in its aggregate's units: "18/50", "20%". */
  total: string | null;
  /** What the total counts: "total score", "competencies achieved", "rated G". */
  caption: string;
  /** "Passed" / "Not passed", or null when the rubric sets no pass line. */
  outcome: string | null;
  passed: boolean | null;
  band: { name: string; tone: string } | null;
  /** The pass line the total is judged against: "Pass at 35/50". */
  passLine: string | null;
}

export interface FeedbackModel {
  header: FeedbackHeader;
  blocks: Array<DomainView | SectionView>;
}

function isEmptyAnswer(value: unknown): boolean {
  if (value === null || value === undefined) return true;
  if (typeof value === "string") return value.trim() === "";
  if (Array.isArray(value)) return value.every(isEmptyAnswer);
  if (isObject(value)) return Object.values(value).every(isEmptyAnswer);
  return false;
}

function listItems(value: unknown): string[] {
  const values = Array.isArray(value) ? value : [value];
  return values
    .map((item) => (typeof item === "string" ? item.trim() : typeof item === "number" ? String(item) : ""))
    .filter((item) => item !== "");
}

/**
 * One answer, by its field's type.
 *
 * A text field whose answer arrived as a list (or the reverse: the engine is
 * a language model) is still shown rather than dropped.
 */
export function answerView(field: RubricField, value: unknown): AnswerView | null {
  if (isEmptyAnswer(value)) return null;
  const base = { role: field.role, label: field.label };
  switch (field.type) {
    case "list": {
      const items = listItems(value);
      return items.length ? { ...base, type: "list", items } : null;
    }
    case "group": {
      const answer = isObject(value) ? value : {};
      const answers = field.fields.flatMap((child) => answerView(child, answer[child.id]) ?? []);
      return answers.length ? { ...base, type: "group", answers } : null;
    }
    case "records": {
      const records = (Array.isArray(value) ? value : [])
        .filter(isObject)
        .map((record) => field.fields.flatMap((child) => answerView(child, record[child.id]) ?? []))
        .filter((answers) => answers.length > 0);
      return records.length ? { ...base, type: "records", records } : null;
    }
    case "singleSelect":
      return { ...base, type: "tag", text: listItems(value).join(", ") };
    case "rating":
      // A rating outside a competency (rare) is written as text.
      return { ...base, type: "text", text: String(value) };
    default: {
      if (field.role === "selector") return { ...base, type: "tag", text: listItems(value).join(", ") };
      if (Array.isArray(value)) {
        const items = listItems(value);
        return items.length ? { ...base, type: "list", items } : null;
      }
      const written = typeof value === "string" ? value.trim() : String(value);
      return written ? { ...base, type: "text", text: written } : null;
    }
  }
}

/** A competency's rating, shaped by the rating kind. */
export function ratingView(rating: Rating, display: Display | null, value: unknown): RatingView | null {
  if (value === null || value === undefined || value === "") return null;
  const tone = ratingTone(rating, display, value);
  if (rating.kind === "boolean") {
    const met = value === true;
    return { shape: "check", text: ratingLabel(rating, value), tone, met };
  }
  if (rating.kind === "range") return { shape: "chip", text: ratingLabel(rating, value), tone };
  return { shape: "grade", text: String(value), tone };
}

/**
 * What good looks like: the descriptor for the best rating.
 *
 * Descriptors are keyed by rating value (`G`, `10`, `true`). A rubric that
 * keys them otherwise still shows its first one rather than none.
 */
function bestDescriptor(rating: Rating, descriptors: Record<string, string>): string | null {
  const best = isEnumerated(rating)
    ? rating.scale?.[0]
    : rating.kind === "boolean"
      ? "true"
      : rating.maximum !== null && rating.maximum !== undefined
        ? formatNumber(rating.maximum)
        : undefined;
  if (best !== undefined && descriptors[best]) return descriptors[best];
  return Object.values(descriptors)[0] ?? null;
}

/** "2 G · 3 A · 2 R": a domain read as rating counts, best first. */
export function countsText(rating: Rating, counts: Record<string, number> | undefined): string | null {
  const scale = rating.scale ?? [];
  if (!counts || scale.length === 0) return null;
  return scale.map((value) => `${counts[value] ?? 0} ${value}`).join(" · ");
}

function passLineText(aggregate: Display["domain"]["aggregate"], passAtLeast: number | null, max: number | null): string | null {
  if (passAtLeast === null) return null;
  return `Pass at ${formatAggregate(aggregate, passAtLeast, max)}`;
}

/** What a station total counts, in words, by its aggregate. */
export function totalCaption(display: Display | null, rating: Rating): string {
  switch (display?.total.aggregate) {
    case "ragShare":
    case "ragCounts": {
      const best = rating.scale?.[0];
      const tone = display?.tones.find((rule) => rule.value !== undefined && rule.value === best)?.tone ?? null;
      return best === undefined ? "of competencies at the best grade" : `of competencies graded ${gradeWord(best, tone)}`;
    }
    case "percentAchieved":
      return "achieved";
    case "mean":
      return "average score";
    default:
      return "total score";
  }
}

/**
 * The whole screen for one result.
 *
 * Totals come from the backend (`result.totals`) and are only written out
 * here. A nullable domain the result left empty is an alternative the
 * candidate did not sit (Ortho has four; one is marked), so it is hidden
 * rather than shown as a row of blanks.
 */
export function feedbackModel(rubric: MarkingRubric, result: MarkedResult, heading = "Your mark"): FeedbackModel {
  const display = readDisplay(rubric.display);
  const rating = rubric.rating;
  const payload = result.payload;
  const totals = result.totals ?? null;
  const domainTotals = new Map((totals?.domains ?? []).map((domain) => [domain.id, domain]));

  const blocks: Array<DomainView | SectionView> = [];
  for (const section of readSections(rubric.structure)) {
    if (section.kind === "field") {
      const answer = answerView(section.field, payload[section.field.id]);
      if (answer) blocks.push({ kind: "section", id: section.field.id, title: section.field.label, answers: [answer] });
      continue;
    }
    const answer = isObject(payload[section.id]) ? (payload[section.id] as JsonObject) : null;
    if (section.kind === "section") {
      const answers = section.fields.flatMap((field) => answerView(field, answer?.[field.id]) ?? []);
      if (answers.length) blocks.push({ kind: "section", id: section.id, title: section.title, answers });
      continue;
    }
    if (!answer || isEmptyAnswer(answer)) {
      if (section.nullable) continue;
    }
    const ratingField = section.competencyFields.find((field) => field.type === "rating");
    const competencies = section.competencies.flatMap((competency): CompetencyView[] => {
      const given = answer && isObject(answer[competency.id]) ? (answer[competency.id] as JsonObject) : null;
      if (!given) return [];
      return [
        {
          id: competency.id,
          label: competency.label,
          rating: ratingView(rating, display, given[ratingField?.id ?? rating.field]),
          answers: section.competencyFields
            .filter((field) => field.type !== "rating")
            .flatMap((field) => answerView(field, given[field.id]) ?? []),
          hint: bestDescriptor(rating, competency.descriptors),
        },
      ];
    });
    const domainTotal = domainTotals.get(section.id);
    const aggregate = display?.domain.aggregate ?? null;
    blocks.push({
      kind: "domain",
      id: section.id,
      title: section.title,
      aggregate:
        aggregate === "ragCounts"
          ? countsText(rating, domainTotal?.counts)
          : aggregate && domainTotal
            ? formatAggregate(aggregate, domainTotal.value, display?.domain.max ?? null)
            : null,
      passed: domainTotal?.passed ?? null,
      passLine: display ? passLineText(display.domain.aggregate, display.domain.passAtLeast, display.domain.max) : null,
      competencies,
      answers: section.fields.flatMap((field) => answerView(field, answer?.[field.id]) ?? []),
    });
  }

  const band = bandFor(display, totals?.total ?? null);
  return {
    header: {
      heading,
      total: display && totals ? formatAggregate(display.total.aggregate, totals.total, display.total.max) : null,
      caption: totalCaption(display, rating),
      outcome: passWord(totals?.passed),
      passed: totals?.passed ?? null,
      band: band ? { name: bandName(band), tone: band.tone } : null,
      passLine: display ? passLineText(display.total.aggregate, display.total.passAtLeast, display.total.max) : null,
    },
    blocks,
  };
}
