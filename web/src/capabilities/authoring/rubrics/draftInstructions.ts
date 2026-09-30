import { parsePath, setAt } from "@/capabilities/authoring/rubrics/jsonPath";
import type { RubricStructure } from "@/capabilities/authoring/rubrics/rubricEdits";

/** One suggestion from `POST …/rubrics/draft-instructions`, as much of it as is needed here. */
export interface InstructionSuggestion {
  path: string;
  text: string;
  has_instructions: boolean;
}

/**
 * The suggested wording written into every place that has none yet.
 *
 * The backend answers one suggestion per place that carries instructions
 * (domain, competency, section, field), each at the same index path a problem
 * uses. Instructions an author already wrote are never replaced: a suggestion
 * only fills a gap. Returns the new structure and how many places it filled,
 * so the screen can say "Filled 7 places" rather than nothing.
 */
export function applyInstructionSuggestions(
  structure: RubricStructure,
  suggestions: readonly InstructionSuggestion[],
): { structure: RubricStructure; filled: number } {
  let next = structure;
  let filled = 0;
  for (const suggestion of suggestions) {
    if (suggestion.has_instructions || suggestion.text.trim() === "") continue;
    next = setAt(next, [...parsePath(suggestion.path), "instructions"], suggestion.text);
    filled += 1;
  }
  return { structure: next, filled };
}
