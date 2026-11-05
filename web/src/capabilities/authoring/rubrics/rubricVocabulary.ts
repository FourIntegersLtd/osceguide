/**
 * The words the rubric builder offers, one list per choice.
 *
 * Every value here is one the backend's `rubrics/validation.py` accepts (its
 * `RATING_KINDS`, `FIELD_TYPES`, `FIELD_ROLES` and so on). The label is what an
 * author reads; the hint is the one line that tells them when to pick it. If
 * the backend adds a value, add it here too — the builder never invents one.
 */

export interface Choice<Value extends string> {
  value: Value;
  label: string;
  hint: string;
}

export type RatingKind = "rag" | "scale" | "range" | "boolean";
export type SectionKind = "domain" | "section" | "field";
export type FieldType = "rating" | "shortText" | "longText" | "list" | "singleSelect" | "group" | "records";
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
export type DomainAggregate = "ragCounts" | "sum" | "mean" | "percentAchieved";
export type TotalAggregate = "ragShare" | "sum" | "mean" | "percentAchieved";
export type Tone = "excellent" | "good" | "fair" | "weak" | "poor";
export type DisplayLabelKey =
  | "domainSubtitle"
  | "domainPassLabel"
  | "totalTitle"
  | "trendSubtitle"
  | "passLabel";

export const RATING_KINDS: readonly Choice<RatingKind>[] = [
  { value: "rag", label: "Red / Amber / Green", hint: "Three grades, G best and R worst." },
  { value: "scale", label: "Named scale", hint: "Your own grades, best first (e.g. Excellent, Good, Fair, Poor)." },
  { value: "range", label: "Number range", hint: "A score between a minimum and a maximum, e.g. 0 to 10." },
  { value: "boolean", label: "Met / not met", hint: "Each competency is either met or not." },
];

export const SECTION_KINDS: readonly Choice<SectionKind>[] = [
  { value: "domain", label: "Rated domain", hint: "Competencies, each rated and answered the same way." },
  { value: "section", label: "Written section", hint: "Fields the marker writes once, with no rating." },
  { value: "field", label: "Single field", hint: "One answer on its own, e.g. an overall summary." },
];

export const FIELD_TYPES: readonly Choice<FieldType>[] = [
  { value: "rating", label: "Rating", hint: "The competency's grade, on the marking scheme's rating." },
  { value: "shortText", label: "Short text", hint: "A line: a name, a heading, a verdict." },
  { value: "longText", label: "Long text", hint: "A paragraph: evidence, an explanation." },
  { value: "list", label: "List", hint: "Several short lines, e.g. actions to take." },
  { value: "singleSelect", label: "Pick one", hint: "One of the options you list." },
  { value: "group", label: "Group", hint: "A few fields answered together, once." },
  { value: "records", label: "Records", hint: "A repeating group, e.g. one row per finding." },
];

export const FIELD_ROLES: readonly Choice<FieldRole>[] = [
  { value: "rating", label: "Rating", hint: "The grade itself." },
  { value: "evidence", label: "Evidence", hint: "What the candidate said or did." },
  { value: "explanation", label: "Explanation", hint: "Why the grade was given." },
  { value: "strength", label: "Strength", hint: "Shown as something done well." },
  { value: "improvement", label: "Improvement", hint: "Shown as something to work on." },
  { value: "action", label: "Action", hint: "A next step for the candidate." },
  { value: "flag", label: "Flag", hint: "A concern the reader must not miss." },
  { value: "summary", label: "Summary", hint: "An overall comment." },
  { value: "selector", label: "Selector", hint: "Picks which variant of the station applied." },
  { value: "other", label: "Other", hint: "Shown plainly, with no special treatment." },
];

export const FIELD_SOURCES: readonly Choice<"marker" | "system">[] = [
  { value: "marker", label: "The marker", hint: "The marking model writes it." },
  { value: "system", label: "The platform", hint: "Filled in after marking, never by the model." },
];

export const DOMAIN_AGGREGATES: readonly Choice<DomainAggregate>[] = [
  { value: "ragCounts", label: "Count each grade", hint: "How many G, A and R a domain got." },
  { value: "sum", label: "Sum", hint: "Add the domain's ratings." },
  { value: "mean", label: "Average", hint: "The mean of the domain's ratings." },
  { value: "percentAchieved", label: "Percent achieved", hint: "Share of the best possible, 0 to 100." },
];

export const TOTAL_AGGREGATES: readonly Choice<TotalAggregate>[] = [
  { value: "ragShare", label: "Share at the best grade", hint: "Percent of ratings at the top of the scale." },
  { value: "sum", label: "Sum", hint: "Add every rating in the station." },
  { value: "mean", label: "Average", hint: "The mean of every rating." },
  { value: "percentAchieved", label: "Percent achieved", hint: "Share of the best possible, 0 to 100." },
];

export const TONES: readonly Choice<Tone>[] = [
  { value: "excellent", label: "Excellent", hint: "Drawn green." },
  { value: "good", label: "Good", hint: "Drawn green." },
  { value: "fair", label: "Fair", hint: "Drawn amber." },
  { value: "weak", label: "Weak", hint: "Drawn red." },
  { value: "poor", label: "Poor", hint: "Drawn red." },
];

export const DISPLAY_LABELS: readonly Choice<DisplayLabelKey>[] = [
  { value: "domainSubtitle", label: "Domain chart subtitle", hint: "Under “Domain performance”." },
  { value: "domainPassLabel", label: "Domain pass line label", hint: "Written on the domain pass line." },
  { value: "totalTitle", label: "Station total title", hint: "Heads the total on the feedback page." },
  { value: "trendSubtitle", label: "Trend chart subtitle", hint: "Under “Performance trend”." },
  { value: "passLabel", label: "Pass line label", hint: "Written on the station pass line." },
];

/** The label for a value in a list, or the value itself when the list does not know it. */
export function labelFor<Value extends string>(choices: readonly Choice<Value>[], value: unknown): string {
  return choices.find((choice) => choice.value === value)?.label ?? String(value ?? "");
}

/** What the author may hide from the candidate's feedback page, in the board's wording. */
export const CANDIDATE_SEES: readonly Choice<string>[] = [
  { value: "overall", label: "Overall result and band", hint: "The total, outcome and band." },
  { value: "areaScores", label: "Score per area", hint: "The figure each domain gets." },
  { value: "wentWell", label: "What went well", hint: "Fields with the Strength role." },
  { value: "workOn", label: "What to work on", hint: "Fields with the Improvement or Action role." },
  { value: "quotes", label: "Transcript quotes", hint: "Fields with the Evidence role." },
];

export const FEEDBACK_TONES: readonly Choice<string>[] = [
  { value: "supportive", label: "Supportive and direct", hint: "Warm, plain and specific." },
  { value: "formal", label: "Formal examiner", hint: "Impersonal, as a mark scheme." },
  { value: "brief", label: "Brief", hint: "Short sentences, no padding." },
];
