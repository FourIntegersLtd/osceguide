import { getAt, isJsonObject, parsePath, pathText, type JsonPath } from "@/capabilities/authoring/rubrics/jsonPath";
import type { RubricStructure } from "@/capabilities/authoring/rubrics/rubricEdits";

/**
 * Pinning the backend's problems to the inputs they name.
 *
 * `POST …/rubrics/preview` answers every problem with the path of the thing it
 * is about (`sections[0].competencies[1].id`), written the way `jsonPath.ts`
 * writes an input's path. So an input asks "what is wrong with me" by its own
 * path, and a card asks "is anything wrong inside me" by its prefix. Nothing
 * here re-implements a rule: the backend is the one validator.
 */

export interface Problem {
  path: string;
  message: string;
}

/** The messages about exactly this path. */
export function problemsAt(problems: readonly Problem[], path: JsonPath): string[] {
  const target = pathText(path);
  return problems.filter((problem) => problem.path === target).map((problem) => problem.message);
}

/** How many problems are at this path or anywhere inside it. */
export function problemsWithin(problems: readonly Problem[], path: JsonPath): number {
  const target = pathText(path);
  if (target === "") return problems.length;
  return problems.filter(
    (problem) => problem.path === target || problem.path.startsWith(`${target}.`) || problem.path.startsWith(`${target}[`),
  ).length;
}

/** The builder tab a problem is fixed on. */
export type BuilderTab = "structure" | "rating" | "display";

export function tabFor(problem: Problem): BuilderTab {
  if (problem.path === "rating" || problem.path.startsWith("rating.")) return "rating";
  if (problem.path === "display" || problem.path.startsWith("display.")) return "display";
  return "structure";
}

function nameOf(value: unknown, keys: readonly string[], fallback: string): string {
  if (!isJsonObject(value)) return fallback;
  for (const key of keys) {
    const text = value[key];
    if (typeof text === "string" && text.trim()) return text.trim();
  }
  return fallback;
}

const KEY_WORDS: Record<string, string> = {
  rating: "Rating",
  display: "Results & dashboard",
  domain: "Domain results",
  total: "Station total",
  tones: "Tone",
  bands: "Band",
  labels: "Labels",
  competencyFields: "Competency fields",
  fields: "Fields",
  competencies: "Competencies",
  descriptors: "Descriptors",
  options: "Options",
  id: "id",
};

/**
 * Where a problem is, in words an author recognises: `sections[0].competencies[1].id`
 * reads "History › Rapport › id" rather than the path.
 */
export function placeLabel(structure: RubricStructure, path: string): string {
  const segments = parsePath(path);
  const words: string[] = [];
  for (let index = 0; index < segments.length; index += 1) {
    const segment = segments[index];
    const next = segments[index + 1];
    if (typeof segment === "string" && typeof next === "number") {
      const item = getAt(structure, segments.slice(0, index + 2));
      if (segment === "sections") words.push(nameOf(item, ["title", "id"], `Section ${next + 1}`));
      else if (segment === "competencies") words.push(nameOf(item, ["label", "id"], `Competency ${next + 1}`));
      else if (segment === "fields" || segment === "competencyFields") words.push(nameOf(item, ["label", "id"], `Field ${next + 1}`));
      else words.push(`${KEY_WORDS[segment] ?? segment} ${next + 1}`);
      index += 1;
      continue;
    }
    if (typeof segment === "string") {
      if (segment === "field" && index > 0) {
        words.push(nameOf(getAt(structure, segments.slice(0, index + 1)), ["label", "id"], "Field"));
        continue;
      }
      words.push(KEY_WORDS[segment] ?? segment);
    }
  }
  return words.join(" › ") || "Rubric";
}

/**
 * The problems a refusal carried. A publish of a draft that has problems is
 * refused with `invalid_rubric` and `details.errors`, the same `{path, message}`
 * items the preview answers; anything else in `details` is ignored.
 */
export function problemsFromDetails(details: Record<string, unknown> | null): Problem[] {
  const errors = details?.errors;
  if (!Array.isArray(errors)) return [];
  return errors.flatMap((item) =>
    isJsonObject(item) && typeof item.path === "string" && typeof item.message === "string"
      ? [{ path: item.path, message: item.message }]
      : [],
  );
}
